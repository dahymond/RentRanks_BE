import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core_app.models import User, Profile, ProfileClaimRequest
import jwt
import datetime
# from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password


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
# @csrf_exempt
# @require_http_methods(["POST"])
# def social_login(request):
#     try:
#         data = json.loads(request.body)

#         name_parts = data.get("name", "").split(" ")
#         first_name = name_parts[0] if len(name_parts) > 0 else ""
#         last_name = name_parts[1] if len(name_parts) > 1 else ""

#         email = data.get("email")
#         provider = data.get("provider", "")
#         google_id = data.get("google_id", "")
#         facebook_id = data.get("facebook_id", "")
#         access_token = data.get("access_token", "")
#         picture = data.get("picture", "")

#         if not email:
#             return JsonResponse({"error": "Email is required"}, status=400)

#         user_defaults = {
#             "first_name": first_name,
#             "last_name": last_name,
#             "access_token": access_token,
#             "picture": picture,
#         }

#         if provider == "google":
#             user_defaults["google_id"] = google_id
#         elif provider == "facebook":
#             user_defaults["facebook_id"] = facebook_id
#         else:
#             return JsonResponse({"error": "Unsupported provider"}, status=400)
        
#         # print(email, user_defaults)
        
#         user, created = User.objects.update_or_create(email=email, defaults=user_defaults)

#         token, expiry = generate_jwt(user)
        
#         return JsonResponse({
#             "status": "successful",
#             "user_id": user.id,
#             "access_token": token,
#             "exp": expiry,
#             "new_user": created
#             })

#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
    


# @csrf_exempt
# def credentials_login(request):
#     if request.method != 'POST':
#         return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
#     try:
#         data = json.loads(request.body)
#         email = data.get('email')
#         password = data.get('password')
        
#         if not email or not password:
#             return JsonResponse({"error": "Email and password are required"}, status=400)
        
#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return JsonResponse({"error": "Invalid credentials"}, status=401)
        
#         if not user.password or not check_password(password, user.password):
#             return JsonResponse({"error": "Invalid credentials"}, status=401)
        
#         token, expiry = generate_jwt(user)
        
#         return JsonResponse({
#             "status": "successful",
#             "user_id": user.id,
#             "access_token": token,
#             "exp": expiry
#         })
        
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
    

# @csrf_exempt
# def register(request):
#     if request.method != 'POST':
#         return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
#     try:
#         data = json.loads(request.body)
#         email = data.get('email')
#         password = data.get('password')
#         first_name = data.get('first_name')
#         role = data.get('role')
        
#         if not all([email, password, first_name, role]):
#             return JsonResponse({"error": "All fields are required"}, status=400)
        
#         if role not in [choice[0] for choice in User.ROLE_CHOICES]:
#             return JsonResponse({"error": "Invalid role"}, status=400)
        
#         if User.objects.filter(email=email).exists():
#             return JsonResponse({"error": "Email already exists"}, status=400)
        
#         hashed_password = make_password(password)
#         user = User.objects.create(
#             email=email,
#             first_name=first_name,
#             last_name=data.get('last_name', ''),
#             password=hashed_password,
#             role=role,
#             verified=False
#         )
        
#         token, expiry = generate_jwt(user)
        
#         return JsonResponse({
#             "status": "successful",
#             "user_id": user.id,
#             "access_token": token,
#             "exp": expiry
#         })
        
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
    

@csrf_exempt
@require_http_methods(["POST"])
def social_login(request):
    try:
        data = json.loads(request.body)

        # Extract basic user info
        name_parts = data.get("name", "").split(" ")
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        email = data.get("email")
        provider = data.get("provider", "").lower()
        picture = data.get("picture", "")

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        # Validate provider
        if provider not in ["google", "facebook"]:
            return JsonResponse({"error": "Unsupported provider"}, status=400)

        # Prepare user data
        user_defaults = {
            "first_name": first_name,
            "last_name": last_name,
            "picture": picture,
            "access_token": data.get("access_token", ""),
            f"{provider}_id": data.get(f"{provider}_id", ""),
            "verified": True  # Social logins are typically verified
        }

        # Create or update user
        user, created = User.objects.update_or_create(
            email=email,
            defaults=user_defaults
        )

        # Profile handling logic
        profile = Profile.objects.filter(email=user.email).first()
        claim_created = False

        if not profile:
            # Create new profile if none exists
            profile = Profile.objects.create(
                full_name=f"{user.first_name} {user.last_name}".strip(),
                email=user.email,
                role=user.role if hasattr(user, 'role') else 'tenant',
                picture=user.picture
            )
        elif not profile.is_claimed and profile.email == user.email:
            # Create claim request if profile exists with matching email
            ProfileClaimRequest.objects.create(
                profile=profile,
                user=user,
                status="pending"
            )
            claim_created = True

        # Generate JWT token
        token, expiry = generate_jwt(user)
        
        return JsonResponse({
            "status": "successful",
            "user_id": user.id,
            "access_token": token,
            "exp": expiry,
            "new_user": created,
            "profile": {
                "id": profile.id if profile else None,
                "is_claimed": profile.is_claimed if profile else False,
                "claim_required": not profile.is_claimed and profile.email == user.email if profile else False,
                "claim_created": claim_created
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def credentials_login(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({"error": "Email and password are required"}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"error": "Invalid credentials"}, status=401)
        
        if not user.password or not check_password(password, user.password):
            return JsonResponse({"error": "Invalid credentials"}, status=401)
        
        # Check for existing profile and claim status
        profile = Profile.objects.filter(email=user.email).first()
        profile_data = None
        if profile:
            profile_data = {
                "id": profile.id,
                "is_claimed": profile.is_claimed,
                "claim_pending": ProfileClaimRequest.objects.filter(
                    profile=profile, 
                    user=user,
                    status="pending"
                ).exists()
            }
        
        token, expiry = generate_jwt(user)
        
        return JsonResponse({
            "status": "successful",
            "user_id": user.id,
            "access_token": token,
            "exp": expiry,
            "profile": profile_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def register(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        role = data.get('role')
        
        if not all([email, password, first_name, role]):
            return JsonResponse({"error": "All fields are required"}, status=400)
        
        if role not in [choice[0] for choice in User.ROLE_CHOICES]:
            return JsonResponse({"error": "Invalid role"}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already exists"}, status=400)
        
        hashed_password = make_password(password)
        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=data.get('last_name', ''),
            password=hashed_password,
            role=role,
            verified=False
        )
        
        # Profile creation logic
        profile = Profile.objects.filter(email=email).first()
        claim_created = False
        
        if not profile:
            profile = Profile.objects.create(
                full_name=f"{user.first_name} {user.last_name}".strip(),
                email=user.email,
                role=user.role,
                is_claimed = True
            )
        elif not profile.is_claimed:
            ProfileClaimRequest.objects.create(
                profile=profile,
                user=user,
                status="pending"
            )
            claim_created = True
        
        token, expiry = generate_jwt(user)
        
        return JsonResponse({
            "status": "successful",
            "user_id": user.id,
            "access_token": token,
            "exp": expiry,
            "profile": {
                "id": profile.id,
                "is_claimed": profile.is_claimed,
                "claim_required": not profile.is_claimed and profile.email == user.email,
                "claim_created": claim_created
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# @csrf_exempt
# def claim_profile(request):
#     if request.method != 'POST':
#         return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
#     try:
#         data = json.loads(request.body)
#         profile_id = data.get('profile_id')
#         user_id = data.get('user_id')
        
#         if not all([profile_id, user_id]):
#             return JsonResponse({"error": "Profile ID and User ID are required"}, status=400)
        
#         try:
#             user = User.objects.get(id=user_id)
#             profile = Profile.objects.get(id=profile_id)
#         except (User.DoesNotExist, Profile.DoesNotExist):
#             return JsonResponse({"error": "Invalid user or profile"}, status=404)
        
#         # Verify user can claim this profile
#         if profile.is_claimed:
#             return JsonResponse({"error": "Profile already claimed"}, status=400)
        
#         if profile.email and profile.email != user.email:
#             return JsonResponse({"error": "You can only claim profiles matching your email"}, status=403)
        
#         # Create claim request or directly claim if email matches
#         if profile.email == user.email:
#             profile.is_claimed = True
#             profile.claimed_by = user
#             profile.save()
#             status = "claimed"
#         else:
#             ProfileClaimRequest.objects.create(
#                 profile=profile,
#                 user=user,
#                 status="pending"
#             )
#             status = "claim_requested"
        
#         return JsonResponse({
#             "status": status,
#             "profile_id": profile.id,
#             "user_id": user.id
#         })
        
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)