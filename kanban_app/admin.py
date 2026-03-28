from django.contrib import admin

from .models import Board, Comment, Task


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner")
    search_fields = ("title", "owner__email")
    filter_horizontal = ("members",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "board",
        "status",
        "priority",
        "due_date",
        "creator",
        "assignee",
        "reviewer",
    )
    list_filter = ("status", "priority", "board")
    search_fields = ("title", "description")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "author", "created_at")
    search_fields = ("content", "author__email")