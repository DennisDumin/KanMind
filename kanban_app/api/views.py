from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import DestroyAPIView, ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from kanban_app.models import Board, Comment, Task
from .permissions import (
    IsBoardOwner,
    IsBoardOwnerOrMember,
    IsCommentAuthor,
    IsTaskBoardMember,
    IsTaskCreatorOrBoardOwner,
    is_board_member,
    is_board_owner,
)
from .serializers import (
    BoardDetailSerializer,
    BoardListSerializer,
    BoardUpdateResponseSerializer,
    BoardWriteSerializer,
    CommentCreateSerializer,
    CommentReadSerializer,
    EmailCheckQuerySerializer,
    TaskReadSerializer,
    TaskWriteSerializer,
    UserPreviewSerializer,
)


class BoardViewSet(viewsets.ModelViewSet):
    """ViewSet for board CRUD operations with role-based permissions."""

    queryset = Board.objects.select_related("owner").prefetch_related(
        "members",
        "tasks",
    )
    serializer_class = BoardListSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        """Return boards where the user is owner or member."""
        user = self.request.user
        return self.queryset.filter(
            Q(owner=user) | Q(members=user)
        ).distinct()

    def get_serializer_class(self):
        """Return the appropriate serializer based on the current action."""
        serializer_map = {
            "list": BoardListSerializer,
            "retrieve": BoardDetailSerializer,
            "create": BoardWriteSerializer,
            "partial_update": BoardWriteSerializer,
        }
        return serializer_map.get(self.action, BoardListSerializer)

    def get_permissions(self):
        """Return permissions based on the current action."""
        permission_map = {
            "retrieve": [IsAuthenticated(), IsBoardOwnerOrMember()],
            "partial_update": [IsAuthenticated(), IsBoardOwnerOrMember()],
            "destroy": [IsAuthenticated(), IsBoardOwner()],
        }
        return permission_map.get(self.action, [IsAuthenticated()])

    def create(self, request, *args, **kwargs):
        """Create a new board and return the board list representation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = serializer.save()
        data = BoardListSerializer(board).data
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """Update a board and return the update response representation."""
        board = self.get_object()
        serializer = self.get_serializer(
            board,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        board = serializer.save()
        data = BoardUpdateResponseSerializer(board).data
        return Response(data, status=status.HTTP_200_OK)


class EmailCheckView(APIView):
    """Lookup a user by email address and return a preview."""

    permission_classes = [IsAuthenticated]
    serializer_class = EmailCheckQuerySerializer

    def get(self, request):
        """Return user preview data for the given email query parameter."""
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = get_object_or_404(User, email__iexact=email)
        data = UserPreviewSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for task creation, update and deletion with board membership checks."""

    queryset = Task.objects.select_related(
        "board",
        "creator",
        "assignee",
        "reviewer",
    ).prefetch_related("comments")
    serializer_class = TaskReadSerializer
    http_method_names = ["post", "patch", "delete"]

    def get_queryset(self):
        """Return tasks from boards where the user is owner or member."""
        user = self.request.user
        return self.queryset.filter(
            Q(board__owner=user) | Q(board__members=user)
        ).distinct()

    def get_serializer_class(self):
        """Return the write serializer for create and update actions."""
        if self.action in ["create", "partial_update"]:
            return TaskWriteSerializer
        return TaskReadSerializer

    def get_permissions(self):
        """Return permissions based on the current action."""
        permission_map = {
            "partial_update": [IsAuthenticated(), IsTaskBoardMember()],
            "destroy": [IsAuthenticated(), IsTaskCreatorOrBoardOwner()],
        }
        return permission_map.get(self.action, [IsAuthenticated()])

    def create(self, request, *args, **kwargs):
        """Create a new task and set the requesting user as creator."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(creator=request.user)
        data = TaskReadSerializer(task).data
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """Update a task and return the read representation."""
        task = self.get_object()
        serializer = self.get_serializer(
            task,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        data = TaskReadSerializer(task).data
        return Response(data, status=status.HTTP_200_OK)


class AssignedToMeTaskListView(ListAPIView):
    """List all tasks assigned to the currently authenticated user."""

    serializer_class = TaskReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return tasks where the current user is the assignee."""
        return Task.objects.select_related(
            "assignee",
            "reviewer",
        ).prefetch_related("comments").filter(
            assignee=self.request.user
        )


class ReviewingTaskListView(ListAPIView):
    """List all tasks where the current user is the reviewer."""

    serializer_class = TaskReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return tasks where the current user is the reviewer."""
        return Task.objects.select_related(
            "assignee",
            "reviewer",
        ).prefetch_related("comments").filter(
            reviewer=self.request.user
        )


class CommentListCreateView(ListCreateAPIView):
    """List and create comments on a task with board membership checks."""

    permission_classes = [IsAuthenticated]
    serializer_class = CommentReadSerializer

    def get_task(self):
        """Return the task and verify the user is a board member."""
        task = get_object_or_404(
            Task.objects.select_related("board"),
            pk=self.kwargs["task_id"],
        )
        if not (
            is_board_owner(self.request.user, task.board)
            or is_board_member(self.request.user, task.board)
        ):
            raise PermissionDenied("You must be a board member.")
        return task

    def get_queryset(self):
        """Return all comments for the given task."""
        task = self.get_task()
        return task.comments.select_related("author")

    def get_serializer_class(self):
        """Return the create serializer for POST requests."""
        if self.request.method == "POST":
            return CommentCreateSerializer
        return CommentReadSerializer

    def create(self, request, *args, **kwargs):
        """Create a comment on the task and return the read representation."""
        task = self.get_task()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task, author=request.user)
        data = CommentReadSerializer(comment).data
        return Response(data, status=status.HTTP_201_CREATED)


class CommentDestroyView(DestroyAPIView):
    """Delete a comment. Only the comment author is allowed to delete."""

    queryset = Comment.objects.select_related("task", "author")
    permission_classes = [IsAuthenticated, IsCommentAuthor]
    lookup_url_kwarg = "comment_id"

    def get_queryset(self):
        """Return comments filtered by the task from the URL."""
        return self.queryset.filter(task_id=self.kwargs["task_id"])