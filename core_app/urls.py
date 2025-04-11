from django.urls import path
from core_app.views import social_login, refresh_token, credentials_login, register
from core_app.views_reviews_profile import submit_review, get_user_profile, get_user_review_history, review_detail, search_profiles

urlpatterns = [
    # auth
    path('auth/register/', register, name='register'),
    path('auth/login/', credentials_login, name='credentials_login'),
    path("auth/social-login/", social_login),
    path("auth/refresh-token/", refresh_token),
    
    # reviews
    path("reviews/submit-review/", submit_review),
    path('reviews/my-reviews/', get_user_review_history),
    path('reviews/<int:review_id>/', review_detail, name='review-detail'),
    
    # profiles
    path('profiles/search/', search_profiles, name='search-profiles'), # search other profiles
    path("profiles/<int:profile_id>/", get_user_profile), #get user's profile
]