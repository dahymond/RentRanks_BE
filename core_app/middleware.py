import jwt
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from core_app.models import User

from django.http import JsonResponse
from django.conf import settings
import jwt
from django.utils.deprecation import MiddlewareMixin
from .models import User

class JWTAuthenticationMiddleware(MiddlewareMixin):
    EXCLUDED_PATHS = [
        "/auth/login/",
        "/auth/register/",
        "/auth/social-login/",
    ]
    
    def process_request(self, request):
        # Skip OPTIONS requests (pre-flight CORS)
        if request.method == 'OPTIONS':
            return None
          
        # Skip excluded paths
        if request.path in self.EXCLUDED_PATHS:
            return None
        
        auth_header = request.headers.get('Authorization')
        
        # Allow anonymous access (but with request.user = None)
        if not auth_header or not auth_header.startswith('Bearer '):
            request.user = None
            return None
            
        token = auth_header.split(' ')[1]
        
        # print("token:", token)
        
        try:
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = decoded_token.get('user_id')
            
            if not user_id:
                return JsonResponse({'error': 'Invalid token payload'}, status=401)
                
            try:
                user = User.objects.get(id=user_id)
                request.user = user  # Attach full user object
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=401)
                
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)



# disable csrf for only api requests
class DisableCSRFMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith("/api/"):  # Only disable for API requests
            setattr(request, '_dont_enforce_csrf_checks', True)