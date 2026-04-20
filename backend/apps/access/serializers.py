from __future__ import annotations

import secrets

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from apps.access.models import Invitation, Membership, Organization, RoleChoices
from apps.access.services import accept_invitation, bootstrap_organization_owner, invite_user, issue_token

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "is_active", "created_at")


class MembershipSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "organization", "role", "is_default", "is_active")


class UserSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "must_change_password",
            "default_organization",
            "memberships",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined", "memberships")


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    organization_name = serializers.CharField(max_length=255)

    def create(self, validated_data):
        user, organization, token = bootstrap_organization_owner(**validated_data)
        return {"user": user, "organization": organization, "token": token}


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        token = issue_token(user=user, created_by=user, label="login")
        return {"user": user, "token": token}


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return user


class InvitationSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    invited_by = serializers.CharField(source="invited_by.username", read_only=True)

    class Meta:
        model = Invitation
        fields = (
            "id",
            "email",
            "role",
            "status",
            "token",
            "organization",
            "invited_by",
            "expires_at",
            "accepted_at",
            "created_at",
        )
        read_only_fields = ("status", "token", "accepted_at", "created_at")


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=RoleChoices.choices, default=RoleChoices.USER)

    def create(self, validated_data):
        request = self.context["request"]
        return invite_user(
            organization=request.organization,
            invited_by=request.user,
            email=validated_data["email"],
            role=validated_data["role"],
        )


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def create(self, validated_data):
        return accept_invitation(**validated_data)


class UserCreateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=RoleChoices.choices, write_only=True, default=RoleChoices.USER)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")
        read_only_fields = ("id",)

    def create(self, validated_data):
        role = validated_data.pop("role")
        temp_password = secrets.token_urlsafe(12)
        user = User.objects.create_user(**validated_data, password=temp_password, must_change_password=True)
        Membership.objects.create(user=user, organization=self.context["request"].organization, role=role, is_default=True)
        if user.default_organization_id is None:
            user.default_organization = self.context["request"].organization
            user.save(update_fields=["default_organization"])
        return user


class ImpersonationSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_user_id(self, value):
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Target user not found.") from exc

    def create(self, validated_data):
        return impersonate_user(
            admin_user=self.context["request"].user,
            target_user=validated_data["user_id"],
            reason=validated_data.get("reason", ""),
        )
