from rest_framework.permissions import BasePermission


def is_board_owner(user, board):
    """Check if the given user is the owner of the board."""
    return board.owner_id == user.id


def is_board_member(user, board):
    """Check if the given user is a member of the board."""
    return board.members.filter(id=user.id).exists()


class IsBoardOwnerOrMember(BasePermission):
    """Grants access if the user is the board owner or a board member."""

    def has_object_permission(self, request, view, obj):
        return is_board_owner(request.user, obj) or is_board_member(
            request.user,
            obj,
        )


class IsBoardOwner(BasePermission):
    """Grants access only to the owner of the board."""

    def has_object_permission(self, request, view, obj):
        return is_board_owner(request.user, obj)


class IsTaskBoardMember(BasePermission):
    """Grants access if the user is the owner or a member of the task's board."""

    def has_object_permission(self, request, view, obj):
        return (
            is_board_owner(request.user, obj.board)
            or is_board_member(request.user, obj.board)
        )


class IsTaskCreatorOrBoardOwner(BasePermission):
    """Grants access if the user created the task or owns the board."""

    def has_object_permission(self, request, view, obj):
        is_creator = obj.creator_id == request.user.id
        is_owner = is_board_owner(request.user, obj.board)
        return is_creator or is_owner


class IsCommentAuthor(BasePermission):
    """Grants access only to the author of the comment."""

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id