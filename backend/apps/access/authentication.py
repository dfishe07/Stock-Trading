from rest_framework import authentication, exceptions

from apps.access.models import AccessToken


class DatabaseTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).decode("utf-8")
        if not auth:
            return None

        parts = auth.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("Invalid authorization header.")

        token_key = parts[1]
        try:
            token = AccessToken.objects.select_related("user").get(key=token_key)
        except AccessToken.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Invalid token.") from exc

        if not token.is_active or not token.user.is_active:
            raise exceptions.AuthenticationFailed("Token has expired or been revoked.")

        request.auth = token
        return (token.user, token)

    def authenticate_header(self, request):
        return self.keyword

