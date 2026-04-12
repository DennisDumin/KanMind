from django.contrib.auth.models import User
from rest_framework import serializers

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
        """Ensure the requesting user is a member or owner of the board."""
        request = self.context["request"]
        if (
            value.owner_id != request.user.id
            and not user_is_board_member(request.user, value)
        ):
            raise serializers.ValidationError(
                "You must be a member of the board."
            )
        return value

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


class BoardListSerializer(serializers.ModelSerializer):
    """Serializer for the board list view with aggregated counts."""

    member_count = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()
    tasks_to_do_count = serializers.SerializerMethodField()
    tasks_high_prio_count = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Board
        fields = [
            "id",
            "title",
            "member_count",
            "ticket_count",
            "tasks_to_do_count",
            "tasks_high_prio_count",
            "owner_id",
        ]

    def get_member_count(self, obj):
        """Return total member count including the owner."""
        count = obj.members.count()
        if not obj.members.filter(id=obj.owner_id).exists():
            count += 1
        return count

    def get_ticket_count(self, obj):
        """Return the total number of tasks on the board."""
        return obj.tasks.count()

    def get_tasks_to_do_count(self, obj):
        """Return the number of tasks with 'to-do' status."""
        return obj.tasks.filter(status=TaskStatus.TO_DO).count()

    def get_tasks_high_prio_count(self, obj):
        """Return the number of tasks with 'high' priority."""
        return obj.tasks.filter(priority=TaskPriority.HIGH).count()


class BoardWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating boards with member management."""

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


class BoardDetailSerializer(serializers.ModelSerializer):
    """Detailed board serializer including full member and task data."""

    owner_id = serializers.IntegerField(read_only=True)
    members = UserPreviewSerializer(many=True, read_only=True)
    tasks = TaskReadSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "title", "owner_id", "members", "tasks"]


class BoardUpdateResponseSerializer(serializers.ModelSerializer):
    """Response serializer for board updates with expanded owner and member data."""

    owner_data = UserPreviewSerializer(source="owner", read_only=True)
    members_data = UserPreviewSerializer(
        source="members",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Board
        fields = ["id", "title", "owner_data", "members_data"]


class EmailCheckQuerySerializer(serializers.Serializer):
    """Validates the email query parameter for the email check endpoint."""

    email = serializers.EmailField()