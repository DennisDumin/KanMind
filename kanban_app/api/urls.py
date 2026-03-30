from django.urls import path

from .views import (
    AssignedToMeTaskListView,
    BoardViewSet,
    CommentDestroyView,
    CommentListCreateView,
    EmailCheckView,
    ReviewingTaskListView,
    TaskViewSet,
)

board_list = BoardViewSet.as_view({
    "get": "list",
    "post": "create",
})

board_detail = BoardViewSet.as_view({
    "get": "retrieve",
    "patch": "partial_update",
    "delete": "destroy",
})

task_list = TaskViewSet.as_view({
    "post": "create",
})

task_detail = TaskViewSet.as_view({
    "patch": "partial_update",
    "delete": "destroy",
})

app_name = "kanban_app"

urlpatterns = [
    path("boards/", board_list, name="board-list"),
    path("boards/<int:pk>/", board_detail, name="board-detail"),
    path("email-check/", EmailCheckView.as_view(), name="email-check"),
    path("tasks/", task_list, name="task-list"),
    path(
        "tasks/assigned-to-me/",
        AssignedToMeTaskListView.as_view(),
        name="tasks-assigned-to-me",
    ),
    path(
        "tasks/reviewing/",
        ReviewingTaskListView.as_view(),
        name="tasks-reviewing",
    ),
    path("tasks/<int:pk>/", task_detail, name="task-detail"),
    path(
        "tasks/<int:task_id>/comments/",
        CommentListCreateView.as_view(),
        name="task-comments",
    ),
    path(
        "tasks/<int:task_id>/comments/<int:comment_id>/",
        CommentDestroyView.as_view(),
        name="task-comment-delete",
    ),
]