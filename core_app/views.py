import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core_app.models import User
import jwt
import datetime
from django.http import JsonResponse
# from django.contrib.auth import get_user_model
from django.conf import settings

def generate_jwt(user):
    expiry = datetime.datetime.now() + datetime.timedelta(days=1)
    payload = {
        "user_id": user.id,
        "email": user.email,
        "exp": expiry,
        "iat": datetime.datetime.now(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, expiry.timestamp()


def refresh_token(request):
    try:
        user_id = request.user_id
        user = User.objects.get(id=user_id)
        new_token, expiry = generate_jwt(user)
        return JsonResponse({"access_token": new_token, "exp": expiry})
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "Invalid token"}, status=401)


# SOCIAL LOGIN FOR Facebook and Google
@csrf_exempt
@require_http_methods(["POST"])
def social_login(request):
    try:
        data = json.loads(request.body)

        name_parts = data.get("name", "").split(" ")
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        email = data.get("email")
        provider = data.get("provider", "")
        google_id = data.get("google_id", "")
        facebook_id = data.get("facebook_id", "")
        access_token = data.get("access_token", "")
        picture = data.get("picture", "")

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        user_defaults = {
            "first_name": first_name,
            "last_name": last_name,
            "access_token": access_token,
            "picture": picture,
        }

        if provider == "google":
            user_defaults["google_id"] = google_id
        elif provider == "facebook":
            user_defaults["facebook_id"] = facebook_id
        else:
            return JsonResponse({"error": "Unsupported provider"}, status=400)
        
        # print(user_defaults)
        
        user, created = User.objects.update_or_create(email=email, defaults=user_defaults)

        token, expiry = generate_jwt(user)
        
        return JsonResponse({
            "status": "successful",
            "user_id": user.id,
            "access_token": token,
            "exp": expiry,
            "new_user": created
            })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)