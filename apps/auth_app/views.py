"""Auth views: login, logout, refresh."""
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.cookies import (
    clear_auth_cookies,
    set_access_cookie,
    set_refresh_cookie,
)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


def _issue_tokens_response(user, message: str = 'Successfully'):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    response = Response({'success': True, 'message': message})
    set_access_cookie(
        response,
        str(access),
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
    )
    set_refresh_cookie(
        response,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
    )
    return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # public

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(request, username=username, password=password)
        if user is None or not getattr(user, 'enabled', True):
            return Response(
                {'success': False, 'message': 'Login yoki parol noto\'g\'ri'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return _issue_tokens_response(user)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response({'success': True, 'message': 'Logged out'})
        clear_auth_cookies(response)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.COOKIE_REFRESH_NAME)
        if not raw_refresh:
            return Response(
                {'success': False, 'message': 'Refresh token topilmadi'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(raw_refresh)
        except (TokenError, InvalidToken):
            return Response(
                {'success': False, 'message': 'Refresh token yaroqsiz'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access = refresh.access_token
        response = Response({'success': True, 'message': 'Refreshed'})
        set_access_cookie(
            response,
            str(access),
            max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        )
        return response
