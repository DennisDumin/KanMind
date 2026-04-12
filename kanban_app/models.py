from django.contrib.auth.models import User
from django.db import models


class Board(models.Model):
    """Represents a Kanban board owned by a user with optional members."""

    title = models.CharField(max_length=64)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_boards",
    )
    members = models.ManyToManyField(
        User,
        related_name="board_memberships",
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Board"
        verbose_name_plural = "Boards"

    def __str__(self):
        return self.title


class TaskStatus(models.TextChoices):
    """Choices for the current status of a task."""

    TO_DO = "to-do", "To do"
    IN_PROGRESS = "in-progress", "In progress"
    REVIEW = "review", "Review"
    DONE = "done", "Done"


class TaskPriority(models.TextChoices):
    """Choices for the priority level of a task."""

    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class Task(models.Model):
    """Represents a task within a board, with assignment and review workflow."""

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
    )
    priority = models.CharField(
        max_length=10,
        choices=TaskPriority.choices,
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
        null=True,
        blank=True,
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="review_tasks",
        null=True,
        blank=True,
    )
    due_date = models.DateField()

    class Meta:
        ordering = ["due_date", "id"]
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Represents a comment on a task, authored by a user."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self):
        return f"Comment {self.id} on {self.task.title}"