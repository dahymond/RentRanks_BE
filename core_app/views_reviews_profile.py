from core_app.models import Profile, ProfileClaimRequest, ProfileClaimDispute, Review
from django.http import JsonResponse
from core_app.models import User
from django.shortcuts import get_object_or_404
import json
import re
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Max
from django.utils import timezone

from django.db.models import Q
from django.core.paginator import Paginator


@csrf_exempt
@require_http_methods(["POST"])
def submit_review(request):
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ["full_name", "role", "rating", "email", "address"]
        if not all(key in data for key in required_fields):
            return JsonResponse({"error": "Missing required fields."}, status=400)

        # Validate address sub-fields
        address_fields = ["line1", "city", "state", "zip_code"]
        if not all(key in data['address'] for key in address_fields):
            return JsonResponse({"error": "Missing required address fields."}, status=400)

        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data['email']):
            return JsonResponse({"error": "Invalid email format."}, status=400)

        # Validate rating
        rating = int(data.get("rating", 3))
        if rating < 1 or rating > 5:
            return JsonResponse({"error": "Rating must be between 1 and 5."}, status=400)

        # Get authenticated user (if not anonymous)
        user = None
        if not data.get('is_anonymous', False):
            if not request.user:
                return JsonResponse({"error": "Authentication required for non-anonymous reviews."}, status=401)
            user = request.user

        # Get or create profile with address information
        profile, created = Profile.objects.get_or_create(
            email=data['email'],
            defaults={
                'full_name': data['full_name'],
                'role': data['role'],
                'phone_number': data.get('phone_number'),
                'address_line1': data['address']['line1'],
                'address_line2': data['address'].get('line2'),
                'city': data['address']['city'],
                'state': data['address']['state'],
                'zip_code': data['address']['zip_code'],
            }
        )

        # If profile exists, update address if different
        if not created:
            address_changed = (
                profile.address_line1 != data['address']['line1'] or
                profile.city != data['address']['city'] or
                profile.state != data['address']['state'] or
                profile.zip_code != data['address']['zip_code']
            )
            
            if address_changed:
                profile.address_line1 = data['address']['line1']
                profile.address_line2 = data['address'].get('line2')
                profile.city = data['address']['city']
                profile.state = data['address']['state']
                profile.zip_code = data['address']['zip_code']
                profile.save()

        # Check if profile details match if not newly created
        if not created:
            if (profile.full_name != data['full_name'] or 
                profile.role != data['role']):
                return JsonResponse({
                    "error": "Profile details don't match existing profile with this email."
                }, status=400)

        # Check if user is reviewing themselves
        if user and profile.email == user.email:
            return JsonResponse({"error": "You cannot review yourself"}, status=400)

        # Create review
        review = Review.objects.create(
            reviewer=user if not data.get('is_anonymous', False) else None,
            profile=profile,
            rating=rating,
            comment=data.get('comment', ""),
            is_anonymous=data.get('is_anonymous', False)
        )
        
        return JsonResponse({
            "success": True,
            "review_id": review.id,
            "profile_id": profile.id,
            "profile_claimed": profile.is_claimed,
            "is_anonymous": review.is_anonymous,
            "profile": {
                "full_name": profile.full_name,
                "email": profile.email,
                "role": profile.role,
                "location": profile.location
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except IntegrityError as e:
        return JsonResponse({"error": f"Database error: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def review_detail(request, review_id):
    print("ednpoint reached. review id:", review_id)
    # Authentication check
    if not request.user:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    
    # Authorization check - only reviewer can edit
    if review.reviewer != request.user:
        return JsonResponse({"error": "Not authorized to edit this review"}, status=403)
    
    if request.method == "GET":
        # Get review details
        review_data = {
            "id": str(review.id),
            "profile": {
                "id": str(review.profile.id),
                "name": review.profile.full_name,
                "type": review.profile.role,
                "location": review.profile.location or "Location not specified"
            },
            "rating": review.rating,
            "comment": review.comment,
            "is_anonymous": review.is_anonymous,
            "created_at": review.created_at.strftime("%Y-%m-%d")
        }
        return JsonResponse(review_data)
    
    elif request.method == "PUT":
        # Update review
        try:
            data = json.loads(request.body)
            review.rating = data.get('rating', review.rating)
            review.comment = data.get('comment', review.comment)
            review.is_anonymous = data.get('is_anonymous', review.is_anonymous)
            review.save()
            
            return JsonResponse({
                "message": "Review updated successfully",
                "review": {
                    "id": str(review.id),
                    "rating": review.rating,
                    "comment": review.comment,
                    "is_anonymous": review.is_anonymous
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["GET"])
def get_user_profile(request, profile_id):
    user= request.user
    try:
        profile = Profile.objects.get(id=profile_id)
    except Profile.DoesNotExist:
            profile = Profile.objects.create(
                full_name=f"{user.first_name} {user.last_name or ''}",
                email=user.email,
                role=user.role,
                is_claimed=True,
                claimed_by=user
            )
    
    reviews = Review.objects.filter(profile=profile).select_related("reviewer")
    
    # Calculate average rating and get review count
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    
    # Get most recent review date
    last_review_date = reviews.aggregate(Max('created_at'))['created_at__max']
    
    profile_data = {
        "id": str(profile.id),
        "name": profile.full_name,
        "type": profile.role,  # 'landlord' or 'tenant'
        "rating": round(average_rating, 1),
        "email": profile.email,
        "profileStatus": "Claimed" if profile.is_claimed else "Unclaimed",
        "reviewCount": review_count,
        "location": profile.location or "Location not specified",
        "lastReviewDate": last_review_date.strftime("%Y-%m-%d") if last_review_date else None,
        "canReview": (user and 
                     not (profile.is_claimed and 
                         user.email == profile.email)),
        "reviews": [
            {
                "id": f"r{review.id}",
                "reviewerName": (
                    "Anonymous" if review.is_anonymous 
                    else f"{review.reviewer.first_name} {review.reviewer.last_name}"
                ),
                "date": review.created_at.strftime("%Y-%m-%d"),
                "location": profile.location or "Location not specified",
                "rating": review.rating,
                "comment": review.comment,
            }
            for review in reviews
        ],
    }

    return JsonResponse(profile_data, safe=False)


@csrf_exempt
@require_http_methods(["GET"])
def search_profiles(request):
    # Get search parameters
    search_type = request.GET.get('type', 'tenant')
    search_name = request.GET.get('name', '').strip()
    search_location = request.GET.get('location', '').strip()
    
    # Build query
    query = Q(role=search_type)
    
    if search_name:
        query &= Q(full_name__icontains=search_name)
    
    if search_location:
        query &= (
            Q(city__icontains=search_location) |
            Q(state__icontains=search_location) |
            Q(location__icontains=search_location)
        )
    
    # Get and paginate results
    profiles = Profile.objects.filter(query).select_related('claimed_by')
    
    # Prepare response data
    results = []
    for profile in profiles:
        reviews = profile.reviews.all()
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        last_review = reviews.order_by('-created_at').first()
        
        results.append({
            "id": str(profile.id),
            "name": profile.full_name,
            "type": profile.role,
            "rating": round(avg_rating, 1),
            "reviewCount": reviews.count(),
            "location": profile.location or "Location not specified",
            "lastReviewDate": last_review.created_at.strftime("%Y-%m-%d") if last_review else None
        })
    
    return JsonResponse({"results": results})

@csrf_exempt
@require_http_methods(["GET"])
def get_user_review_history(request):
    # Ensure user is authenticated
    if not request.user:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    # Get all reviews left by this user
    reviews = Review.objects.filter(reviewer=request.user).select_related('profile').order_by('-created_at')
    
    # Organize the response data
    review_history = {
        "reviewer": {
            "id": str(request.user.id),
            "name": f"{request.user.first_name} {request.user.last_name or ''}".strip(),
            "email": request.user.email
        },
        "total_reviews": reviews.count(),
        "reviews": [
            {
                "id": f"r{review.id}",
                "profile": {
                    "id": str(review.profile.id),
                    "name": review.profile.full_name,
                    "type": review.profile.role,
                    "location": review.profile.location or "Location not specified"
                },
                "rating": review.rating,
                "comment": review.comment,
                "is_anonymous": review.is_anonymous,
                "date": review.created_at.strftime("%Y-%m-%d"),
                "can_edit": True  # Since they're the author
            }
            for review in reviews
        ]
    }
    
    return JsonResponse(review_history)



def claim_profile(request):
    
    data = json.loads(request.body)
    profile_id =  data['profile_id']
    try:
        user = request.user
        if not user:
            return JsonResponse({"error": "User not found."}, status=400)
        
        profile = Profile.objects.filter(id=profile_id, is_claimed=False).first()
        if not profile:
            return JsonResponse({"error": "Profile not found or already claimed."}, status=400)

        # Verification (email match or manual admin approval)
        if profile.email and profile.email == user.email:
            profile.is_claimed = True
            profile.claimed_by = user
            profile.save()
            return JsonResponse({"message": "Profile claimed successfully."})
        
        # # This commented out code is useful for when we decide to 
        # # allow admins review profile claim requests before accepting/rejecting
        # # for now, the claim request is handled by the code directly above
        
        # # Create a pending claim request
        # claim_request, created = ProfileClaimRequest.objects.get_or_create(
        #     profile=profile,
        #     user=user
        # )

        # if not created:
        #     return JsonResponse({"message": "You already submitted a claim request."}, status=400)
        
        return JsonResponse({"error": "Verification needed. Contact support."}, status=403)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def dispute_profile_claim(request):
    user = request.user
    profile_id = request.data['profile_id']
    
    profile = Profile.objects.filter(id=profile_id, is_claimed=True).first()
    if not profile:
        return JsonResponse({"error": "Profile not found."}, status=404)

    # Only allow disputes if the user can prove ownership (admin verification needed)
    dispute = ProfileClaimDispute.objects.create(
        profile=profile,
        claimant=user,
        status="pending"
    )
    
    return JsonResponse({"message": "Dispute filed. Awaiting review."})