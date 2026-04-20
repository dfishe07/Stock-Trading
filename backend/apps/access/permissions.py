from __future__ import annotations

from types import SimpleNamespace

from rest_framework.permissions import BasePermission

from apps.access.models import Membership, RoleChoices


ROLE_RANK = {
    RoleChoices.USER: 10,
    RoleChoices.DEVELOPER: 20,
    RoleChoices.ADMIN: 30,
}


def get_current_membership(user, organization):
    if not user.is_authenticated or organization is None:
        return None
    membership = Membership.objects.filter(user=user, organization=organization, is_active=True).first()
    if membership is not None:
        return membership
    if user.is_superuser:
        return SimpleNamespace(role=RoleChoices.ADMIN)
    return None


class MinimumOrganizationRole(BasePermission):
    minimum_role = RoleChoices.USER

    def has_permission(self, request, view):
        organization = getattr(request, "organization", None)
        membership = get_current_membership(request.user, organization)
        if membership is None:
            return False
        return ROLE_RANK[membership.role] >= ROLE_RANK[self.minimum_role]


class IsDeveloperOrAdmin(MinimumOrganizationRole):
    minimum_role = RoleChoices.DEVELOPER


class IsAdmin(MinimumOrganizationRole):
    minimum_role = RoleChoices.ADMIN
