from django.contrib.auth.models import User
from rest_framework import serializers

from kanban_app.models import Board, Comment, Task, TaskPriority, TaskStatus


def user_is_board_member(user, board):
    return board.members.filter(id=user.id).exists()


class UserPreviewSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source="first_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "fullname"]


class CommentReadSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.first_name", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "created_at", "author", "content"]


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["content"]

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content may not be empty.")
        return value


class TaskReadSerializer(serializers.ModelSerializer):
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
        return obj.comments.count()


class TaskWriteSerializer(serializers.ModelSerializer):
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
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                "Title must be at least 3 characters long."
            )
        return value

    def validate_board(self, value):
        request = self.context["request"]
        if not user_is_board_member(request.user, value):
            raise serializers.ValidationError(
                "You must be a member of the board."
            )
        return value

    def validate(self, attrs):
        self._validate_board_change(attrs)
        board = self._get_board(attrs)
        self._validate_member_field(attrs, board, "assignee", "assignee_id")
        self._validate_member_field(attrs, board, "reviewer", "reviewer_id")
        return attrs

    def _validate_board_change(self, attrs):
        if self.instance and "board" in attrs:
            raise serializers.ValidationError(
                {"board": ["Changing the board is not allowed."]}
            )

    def _get_board(self, attrs):
        if self.instance:
            return self.instance.board
        return attrs.get("board")

    def _validate_member_field(self, attrs, board, key, field_name):
        if key not in attrs:
            return
        user = attrs.get(key)
        if user and not user_is_board_member(user, board):
            raise serializers.ValidationError(
                {field_name: ["User must be a member of the board."]}
            )


class BoardListSerializer(serializers.ModelSerializer):
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
        return obj.members.count()

    def get_ticket_count(self, obj):
        return obj.tasks.count()

    def get_tasks_to_do_count(self, obj):
        return obj.tasks.filter(status=TaskStatus.TO_DO).count()

    def get_tasks_high_prio_count(self, obj):
        return obj.tasks.filter(priority=TaskPriority.HIGH).count()


class BoardWriteSerializer(serializers.ModelSerializer):
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
        value = value.strip()
        if len(value) < 3 or len(value) > 64:
            raise serializers.ValidationError(
                "Title must be between 3 and 64 characters."
            )
        return value

    def create(self, validated_data):
        members = validated_data.pop("members", [])
        board = Board.objects.create(
            owner=self.context["request"].user,
            **validated_data,
        )
        board.members.set(members)
        return board

    def update(self, instance, validated_data):
        members = validated_data.pop("members", None)
        instance.title = validated_data.get("title", instance.title)
        instance.save()

        if members is not None:
            instance.members.set(members)

        return instance


class BoardDetailSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(read_only=True)
    members = UserPreviewSerializer(many=True, read_only=True)
    tasks = TaskReadSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "title", "owner_id", "members", "tasks"]


class BoardUpdateResponseSerializer(serializers.ModelSerializer):
    owner_data = UserPreviewSerializer(source="owner", read_only=True)
    members_data = UserPreviewSerializer(
        source="members",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Board
        fields = ["id", "title", "owner_data", "members_data"]