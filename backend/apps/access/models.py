from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import TimeStampedUUIDModel


class RoleChoices(models.TextChoices):
    ADMIN = "admin", "Admin"
    DEVELOPER = "developer", "Developer"
    USER = "user", "User"


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class Organization(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    must_change_password = models.BooleanField(default=False)
    default_organization = models.ForeignKey(
        Organization,
        related_name="default_users",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["username"]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username


class Membership(TimeStampedUUIDModel):
    user = models.ForeignKey(User, related_name="memberships", on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, related_name="memberships", on_delete=models.CASCADE)
    role = models.CharField(max_length=32, choices=RoleChoices.choices, default=RoleChoices.USER)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "organization")
        ordering = ["organization__name", "user__username"]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.organization.slug} ({self.role})"


class InvitationStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class Invitation(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="invitations", on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=32, choices=RoleChoices.choices, default=RoleChoices.USER)
    token = models.CharField(max_length=128, unique=True, default=generate_token)
    invited_by = models.ForeignKey(User, related_name="sent_invitations", null=True, on_delete=models.SET_NULL)
    invited_user = models.ForeignKey(User, related_name="accepted_invitations", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=32, choices=InvitationStatusChoices.choices, default=InvitationStatusChoices.PENDING)
    expires_at = models.DateTimeField(default=default_invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} ({self.organization.slug})"

    @property
    def is_valid(self) -> bool:
        return self.status == InvitationStatusChoices.PENDING and self.expires_at > timezone.now()


class AccessToken(TimeStampedUUIDModel):
    user = models.ForeignKey(User, related_name="access_tokens", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, related_name="issued_tokens", null=True, blank=True, on_delete=models.SET_NULL)
    impersonated_by = models.ForeignKey(
        User,
        related_name="impersonation_tokens",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    key = models.CharField(max_length=128, unique=True, default=generate_token)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    label = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self) -> bool:
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])


class ImpersonationAudit(TimeStampedUUIDModel):
    admin = models.ForeignKey(User, related_name="impersonation_audits", on_delete=models.CASCADE)
    target_user = models.ForeignKey(User, related_name="impersonated_sessions", on_delete=models.CASCADE)
    access_token = models.OneToOneField(
        AccessToken,
        related_name="impersonation_audit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    reason = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
