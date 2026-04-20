from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.access.models import AccessToken, ImpersonationAudit, Invitation, Membership, Organization, RoleChoices, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Trading Platform", {"fields": ("must_change_password", "default_organization")}),
    )
    list_display = ("username", "email", "is_staff", "must_change_password", "default_organization")
    search_fields = ("username", "email")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.is_superuser and obj.default_organization_id:
            Membership.objects.update_or_create(
                user=obj,
                organization=obj.default_organization,
                defaults={
                    "role": RoleChoices.ADMIN,
                    "is_default": True,
                    "is_active": True,
                },
            )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_default", "is_active")
    list_filter = ("role", "organization")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "status", "expires_at", "accepted_at")
    list_filter = ("status", "role", "organization")
    search_fields = ("email", "token")


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "created_by", "impersonated_by", "expires_at", "revoked_at")
    list_filter = ("created_by", "impersonated_by")
    search_fields = ("user__username", "key")


@admin.register(ImpersonationAudit)
class ImpersonationAuditAdmin(admin.ModelAdmin):
    list_display = ("admin", "target_user", "started_at", "ended_at")
    search_fields = ("admin__username", "target_user__username", "reason")
