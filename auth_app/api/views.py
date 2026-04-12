from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegistrationSerializer


def build_auth_response(user, token):
    """Build the standard authentication response with token and user data."""
    return {
        "token": token.key,
        "fullname": user.first_name,
        "email": user.email,
        "user_id": user.id,
    }


class RegistrationView(APIView):
    """Handle user registration and return an authentication token."""

    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def post(self, request):
        """Register a new user and return token with user data."""
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        data = build_auth_response(user, token)
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Handle user login and return an authentication token."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """Authenticate the user and return token with user data."""
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        data = build_auth_response(user, token)
        return Response(data, status=status.HTTP_200_OK)