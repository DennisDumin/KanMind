from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from kanban_app.models import Board, Comment, Task, TaskPriority, TaskStatus


def user_is_board_member(user, board):
    """Check if the given user is a member of the board."""
    return board.members.filter(id=user.id).exists()


class UserPreviewSerializer(serializers.ModelSerializer):
    """Serializes a user with id, email and fullname for preview purposes."""

    fullname = serializers.CharField(source="first_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "fullname"]


class CommentReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for displaying comments with author name."""

    author = serializers.CharField(source="author.first_name", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "created_at", "author", "content"]


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new comment with content validation."""

    class Meta:
        model = Comment
        fields = ["content"]

    def validate_content(self, value):
        """Ensure the comment content is not empty or whitespace."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content may not be empty.")
        return value


class TaskReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for tasks including assignee, reviewer and comment count."""

    assignee = UserPreviewSerializer(read_only=True)
    reviewer = UserPreviewSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "board",
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "reviewer",
            "due_date",
            "comments_count",
        ]

    def get_comments_count(self, obj):
        """Return the number of comments on the task."""
        return obj.comments.count()


class TaskWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating tasks with board membership validation."""

    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
    )
    reviewer_id = serializers.PrimaryKeyRelatedField(
        source="reviewer",
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
    )
    board = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "board",
            "title",
            "description",
            "status",
            "priority",
            "assignee_id",
            "reviewer_id",
            "due_date",
        ]
        read_only_fields = ["id"]

    def validate_title(self, value):
        """Ensure the title is at least 3 characters long."""
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                "Title must be at least 3 characters long."
            )
        return value

    def validate_board(self, value):
        """Validate board exists (404) and user is a member (403)."""
        try:
            board = Board.objects.get(pk=value)
        except Board.DoesNotExist:
            raise NotFound("Board not found.")

        request = self.context["request"]
        if (
            board.owner_id != request.user.id
            and not user_is_board_member(request.user, board)
        ):
            raise PermissionDenied(
                "You must be a member of the board."
            )
        return board

    def validate(self, attrs):
        """Validate board change restrictions and member field assignments."""
        self._validate_board_change(attrs)
        board = self._get_board(attrs)
        self._validate_member_field(attrs, board, "assignee", "assignee_id")
        self._validate_member_field(attrs, board, "reviewer", "reviewer_id")
        return attrs

    def _validate_board_change(self, attrs):
        """Prevent changing the board of an existing task."""
        if self.instance and "board" in attrs:
            raise serializers.ValidationError(
                {"board": ["Changing the board is not allowed."]}
            )

    def _get_board(self, attrs):
        """Return the board from the existing instance or from the new data."""
        if self.instance:
            return self.instance.board
        return attrs.get("board")

    def _validate_member_field(self, attrs, board, key, field_name):
        """Ensure the assigned user is a member or owner of the board."""
        if key not in attrs:
            return
        user = attrs.get(key)
        if (
            user
            and board.owner_id != user.id
            and not user_is_board_member(user, board)
        ):
            raise serializers.ValidationError(
                {field_name: ["User must be a member of the board."]}
            )


class BoardSerializer(serializers.ModelSerializer):
    """Unified serializer for boards. Uses to_representation for different responses."""

    members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Board
        fields = ["id", "title", "members"]
        read_only_fields = ["id"]

    def validate_title(self, value):
        """Ensure the title is between 3 and 64 characters."""
        value = value.strip()
        if len(value) < 3 or len(value) > 64:
            raise serializers.ValidationError(
                "Title must be between 3 and 64 characters."
            )
        return value

    def create(self, validated_data):
        """Create a new board and add the owner and given members."""
        members = validated_data.pop("members", [])
        board = Board.objects.create(
            owner=self.context["request"].user,
            **validated_data,
        )
        board.members.add(self.context["request"].user)
        board.members.add(*members)
        return board

    def update(self, instance, validated_data):
        """Update board title and optionally replace the member list."""
        members = validated_data.pop("members", None)
        instance.title = validated_data.get("title", instance.title)
        instance.save()

        if members is not None:
            instance.members.set(members)

        return instance

    def to_representation(self, instance):
        """Return different representations based on the view action."""
        action = self._get_action()

        if action == "retrieve":
            return self._detail_representation(instance)
        elif action == "update_response":
            return self._update_representation(instance)
        else:
            return self._list_representation(instance)

    def _get_action(self):
        """Determine the current action from view or context."""
        if "view_action" in self.context:
            return self.context["view_action"]

        view = self.context.get("view")
        if view and hasattr(view, "action"):
            return view.action
        return "list"

    def _list_representation(self, instance):
        """Board list representation with aggregated counts."""
        member_count = instance.members.count()
        if not instance.members.filter(id=instance.owner_id).exists():
            member_count += 1

        return {
            "id": instance.id,
            "title": instance.title,
            "member_count": member_count,
            "ticket_count": instance.tasks.count(),
            "tasks_to_do_count": instance.tasks.filter(
                status=TaskStatus.TO_DO,
            ).count(),
            "tasks_high_prio_count": instance.tasks.filter(
                priority=TaskPriority.HIGH,
            ).count(),
            "owner_id": instance.owner_id,
        }

    def _detail_representation(self, instance):
        """Board detail representation with full member and task data."""
        return {
            "id": instance.id,
            "title": instance.title,
            "owner_id": instance.owner_id,
            "members": UserPreviewSerializer(
                instance.members.all(), many=True,
            ).data,
            "tasks": TaskReadSerializer(
                instance.tasks.all(), many=True,
            ).data,
        }

    def _update_representation(self, instance):
        """Board update response with expanded owner and member data."""
        return {
            "id": instance.id,
            "title": instance.title,
            "owner_data": UserPreviewSerializer(instance.owner).data,
            "members_data": UserPreviewSerializer(
                instance.members.all(), many=True,
            ).data,
        }


class EmailCheckQuerySerializer(serializers.Serializer):
    """Validates the email query parameter for the email check endpoint."""

    email = serializers.EmailField()