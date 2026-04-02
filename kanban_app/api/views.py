from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import DestroyAPIView, ListCreateAPIView, ListAPIView
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
    queryset = Board.objects.select_related("owner").prefetch_related(
        "members",
        "tasks",
    )
    serializer_class = BoardListSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            Q(owner=user) | Q(members=user)
        ).distinct()

    def get_serializer_class(self):
        serializer_map = {
            "list": BoardListSerializer,
            "retrieve": BoardDetailSerializer,
            "create": BoardWriteSerializer,
            "partial_update": BoardWriteSerializer,
        }
        return serializer_map.get(self.action, BoardListSerializer)

    def get_permissions(self):
        permission_map = {
            "retrieve": [IsAuthenticated(), IsBoardOwnerOrMember()],
            "partial_update": [IsAuthenticated(), IsBoardOwnerOrMember()],
            "destroy": [IsAuthenticated(), IsBoardOwner()],
        }
        return permission_map.get(self.action, [IsAuthenticated()])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = serializer.save()
        data = BoardListSerializer(board).data
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
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
    permission_classes = [IsAuthenticated]
    serializer_class = EmailCheckQuerySerializer

    def get(self, request):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = get_object_or_404(User, email__iexact=email)
        data = UserPreviewSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related(
        "board",
        "creator",
        "assignee",
        "reviewer",
    ).prefetch_related("comments")
    serializer_class = TaskReadSerializer
    http_method_names = ["post", "patch", "delete"]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            Q(board__owner=user) | Q(board__members=user)
        ).distinct()

    def get_serializer_class(self):
        if self.action in ["create", "partial_update"]:
            return TaskWriteSerializer
        return TaskReadSerializer

    def get_permissions(self):
        permission_map = {
            "partial_update": [IsAuthenticated(), IsTaskBoardMember()],
            "destroy": [IsAuthenticated(), IsTaskCreatorOrBoardOwner()],
        }
        return permission_map.get(self.action, [IsAuthenticated()])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(creator=request.user)
        data = TaskReadSerializer(task).data
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
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
    serializer_class = TaskReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.select_related(
            "assignee",
            "reviewer",
        ).prefetch_related("comments").filter(
            assignee=self.request.user
        )


class ReviewingTaskListView(ListAPIView):
    serializer_class = TaskReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.select_related(
            "assignee",
            "reviewer",
        ).prefetch_related("comments").filter(
            reviewer=self.request.user
        )


class CommentListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentReadSerializer

    def get_task(self):
        task = get_object_or_404(
            Task.objects.select_related("board"),
            pk=self.kwargs["task_id"],
        )
        if not (is_board_owner(self.request.user, task.board) or is_board_member(self.request.user, task.board)):
            raise PermissionDenied("You must be a board member.")
        return task

    def get_queryset(self):
        task = self.get_task()
        return task.comments.select_related("author")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CommentCreateSerializer
        return CommentReadSerializer

    def create(self, request, *args, **kwargs):
        task = self.get_task()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task, author=request.user)
        data = CommentReadSerializer(comment).data
        return Response(data, status=status.HTTP_201_CREATED)


class CommentDestroyView(DestroyAPIView):
    queryset = Comment.objects.select_related("task", "author")
    permission_classes = [IsAuthenticated, IsCommentAuthor]
    lookup_url_kwarg = "comment_id"

    def get_queryset(self):
        return self.queryset.filter(task_id=self.kwargs["task_id"])