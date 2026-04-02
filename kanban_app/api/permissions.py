from rest_framework.permissions import BasePermission


def is_board_owner(user, board):
    return board.owner_id == user.id


def is_board_member(user, board):
    return board.members.filter(id=user.id).exists()


class IsBoardOwnerOrMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return is_board_owner(request.user, obj) or is_board_member(
            request.user,
            obj,
        )


class IsBoardOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return is_board_owner(request.user, obj)


class IsTaskBoardMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return is_board_owner(request.user, obj.board) or is_board_member(request.user, obj.board)


class IsTaskCreatorOrBoardOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        is_creator = obj.creator_id == request.user.id
        is_owner = is_board_owner(request.user, obj.board)
        return is_creator or is_owner


class IsCommentAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id