import jwt
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from core_app.models import User
class JWTAuthenticationMiddleware(MiddlewareMixin):
    EXCLUDED_PATHS = ["/auth/login/", "/auth/social-login/"]  # Add login and other excluded paths here
    
    def process_request(self, request):
        # Exclude specific paths from authentication
        if request.path in self.EXCLUDED_PATHS:
            return None  # Skip authentication for login endpoint
        
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                request.user_id = decoded_token["user_id"]
                # Fetch user here. Attach to request object.
                # Throw error if user not found
            except jwt.ExpiredSignatureError:
                return JsonResponse({"error": "Token expired"}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({"error": "Invalid token"}, status=401)



# disable csrf for only api requests
class DisableCSRFMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith("/api/"):  # Only disable for API requests
            setattr(request, '_dont_enforce_csrf_checks', True)