from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import Invitation, Membership, RoleChoices
from apps.access.permissions import IsAdmin
from apps.access.serializers import (
    ChangePasswordSerializer,
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from apps.access.services import revoke_token

User = get_user_model()


def resolve_request_organization(request):
    header_slug = request.headers.get("X-Organization-Slug")
    memberships = request.user.memberships.select_related("organization").filter(is_active=True)
    if header_slug:
        membership = memberships.filter(organization__slug=header_slug).first()
        if membership:
            return membership.organization
    default_membership = memberships.filter(is_default=True).first()
    if default_membership:
        return default_membership.organization
    if request.user.is_authenticated and request.user.default_organization_id:
        return request.user.default_organization
    fallback = memberships.first()
    return fallback.organization if fallback else None


class OrganizationScopedAPIView(APIView):
    def initial(self, request, *args, **kwargs):
        self.format_kwarg = self.get_format_suffix(**kwargs)
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme
        self.perform_authentication(request)
        request.organization = resolve_request_organization(request)
        self.check_permissions(request)
        self.check_throttles(request)


class OrganizationScopedViewSet(viewsets.GenericViewSet):
    def initial(self, request, *args, **kwargs):
        self.format_kwarg = self.get_format_suffix(**kwargs)
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme
        self.perform_authentication(request)
        request.organization = resolve_request_organization(request)
        self.check_permissions(request)
        self.check_throttles(request)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(
            {
                "token": payload["token"].key,
                "user": UserSerializer(payload["user"]).data,
                "organization": payload["organization"].slug,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        return Response({"token": payload["token"].key, "user": UserSerializer(payload["user"]).data})


class AcceptInvitationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class MeView(OrganizationScopedAPIView):
    def get(self, request):
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "organization": request.organization.slug if request.organization else None,
            }
        )


class LogoutView(OrganizationScopedAPIView):
    def post(self, request):
        token = getattr(request, "auth", None)
        if token:
            revoke_token(token)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(OrganizationScopedAPIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})


class UserViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, OrganizationScopedViewSet):
    queryset = User.objects.all().prefetch_related("memberships__organization")
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in {"create"}:
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(memberships__organization=organization).distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def impersonate(self, request):
        target_user = User.objects.filter(pk=request.data.get("user_id")).first()
        if not target_user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if not Membership.objects.filter(user=target_user, organization=request.organization, is_active=True).exists():
            return Response({"detail": "User is not in the active organization."}, status=status.HTTP_400_BAD_REQUEST)
        from apps.access.services import impersonate_user

        token, audit = impersonate_user(admin_user=request.user, target_user=target_user, reason=request.data.get("reason", ""))
        return Response(
            {
                "token": token.key,
                "audit_id": str(audit.id),
                "user": UserSerializer(target_user).data,
            }
        )


class InvitationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, OrganizationScopedViewSet):
    queryset = Invitation.objects.all().select_related("organization", "invited_by")

    def get_permissions(self):
        return [IsAdmin()]

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(organization=organization)

    def get_serializer_class(self):
        if self.action == "create":
            return InvitationCreateSerializer
        return InvitationSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def invitation_lookup(request):
    token = request.query_params.get("token")
    invitation = Invitation.objects.filter(token=token).select_related("organization").first()
    if not invitation:
        return Response({"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(InvitationSerializer(invitation).data)
