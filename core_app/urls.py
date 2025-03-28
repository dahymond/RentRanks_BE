from django.urls import path
from core_app.views import social_login, refresh_token

urlpatterns = [
    path("auth/social-login/", social_login),
    path("auth/refresh-token/", refresh_token),
]