from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.access.views import (
    AcceptInvitationView,
    ChangePasswordView,
    InvitationViewSet,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    UserViewSet,
    invitation_lookup,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("invitations", InvitationViewSet, basename="invitation")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("accept-invitation/", AcceptInvitationView.as_view(), name="accept-invitation"),
    path("invitation-lookup/", invitation_lookup, name="invitation-lookup"),
    path("", include(router.urls)),
]
