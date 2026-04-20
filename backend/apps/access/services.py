from __future__ import annotations

import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.access.models import AccessToken, ImpersonationAudit, Invitation, InvitationStatusChoices, Membership, Organization
from config.settings import FRONTEND_INVITE_URL

User = get_user_model()


def unique_slug_for_organization(name: str) -> str:
    base_slug = slugify(name) or "organization"
    slug = base_slug
    counter = 2
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def bootstrap_organization_owner(*, username: str, email: str, password: str, organization_name: str, first_name: str = "", last_name: str = ""):
    organization = Organization.objects.create(name=organization_name, slug=unique_slug_for_organization(organization_name))
    user = User.objects.create_user(
        username=username,
        email=email.lower(),
        password=password,
        first_name=first_name,
        last_name=last_name,
        default_organization=organization,
    )
    Membership.objects.create(user=user, organization=organization, role="admin", is_default=True)
    token = issue_token(user=user, created_by=user, label="initial-login")
    from apps.operations.services import record_audit_event

    record_audit_event(
        organization=organization,
        actor=user,
        category="identity",
        verb="register",
        target_type="user",
        target_id=str(user.id),
        payload={"organization": organization.slug},
    )
    return user, organization, token


def issue_token(*, user, created_by=None, impersonated_by=None, ttl_hours: int = 24, label: str = "") -> AccessToken:
    expires_at = timezone.now() + timedelta(hours=ttl_hours)
    return AccessToken.objects.create(
        user=user,
        created_by=created_by,
        impersonated_by=impersonated_by,
        expires_at=expires_at,
        label=label,
    )


def revoke_token(token: AccessToken) -> None:
    token.revoke()


@transaction.atomic
def invite_user(*, organization, invited_by, email: str, role: str) -> Invitation:
    invitation = Invitation.objects.create(
        organization=organization,
        invited_by=invited_by,
        email=email.lower(),
        role=role,
    )
    invite_link = f"{FRONTEND_INVITE_URL}?token={invitation.token}"
    send_mail(
        subject="You have been invited to the trading platform",
        message=f"Use this invitation link to activate your account: {invite_link}",
        from_email=None,
        recipient_list=[invitation.email],
        fail_silently=True,
    )
    from apps.operations.services import record_audit_event

    record_audit_event(
        organization=organization,
        actor=invited_by,
        category="identity",
        verb="invite",
        target_type="invitation",
        target_id=str(invitation.id),
        payload={"email": invitation.email, "role": role},
    )
    return invitation


@transaction.atomic
def accept_invitation(*, token: str, username: str, password: str, first_name: str = "", last_name: str = ""):
    invitation = Invitation.objects.select_for_update().select_related("organization").filter(token=token).first()
    if invitation is None or not invitation.is_valid:
        raise ValueError("Invitation is invalid or expired.")

    user, created = User.objects.get_or_create(
        email=invitation.email.lower(),
        defaults={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "must_change_password": True,
        },
    )
    if not created and user.username != username:
        user.username = username
    user.set_password(password)
    user.must_change_password = True
    if user.default_organization_id is None:
        user.default_organization = invitation.organization
    user.save()

    Membership.objects.update_or_create(
        user=user,
        organization=invitation.organization,
        defaults={"role": invitation.role, "is_default": user.default_organization_id == invitation.organization_id, "is_active": True},
    )

    invitation.invited_user = user
    invitation.status = InvitationStatusChoices.ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["invited_user", "status", "accepted_at", "updated_at"])

    from apps.operations.services import record_audit_event

    record_audit_event(
        organization=invitation.organization,
        actor=user,
        category="identity",
        verb="accept-invitation",
        target_type="invitation",
        target_id=str(invitation.id),
        payload={"email": invitation.email},
    )

    return user


@transaction.atomic
def impersonate_user(*, admin_user, target_user, reason: str = ""):
    token = issue_token(user=target_user, created_by=admin_user, impersonated_by=admin_user, ttl_hours=2, label="impersonation")
    audit = ImpersonationAudit.objects.create(admin=admin_user, target_user=target_user, access_token=token, reason=reason)
    from apps.operations.services import record_audit_event

    membership = target_user.memberships.filter(is_active=True).first()
    record_audit_event(
        organization=membership.organization if membership else None,
        actor=admin_user,
        category="identity",
        verb="impersonate",
        target_type="user",
        target_id=str(target_user.id),
        payload={"reason": reason},
    )
    return token, audit
