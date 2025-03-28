from core_app.models import Profile, ProfileClaimRequest, ProfileClaimDispute, Review
from django.http import JsonResponse
from core_app.models import User
from django.shortcuts import get_object_or_404
import json

def submit_review(request):
    user_id = request.user_id # Authenticated reviewer
    data = json.loads(request.body)
    
    user = get_object_or_404(User, id=user_id)  # Ensure authenticated user
   
    try:
        # Validate required fields
        if not all(key in data for key in ["full_name", "role", "rating"]):
            return JsonResponse({"error": "Missing required fields."}, status=400)

        # Ensure rating is within valid range (1-5)
        rating = int(data.get("rating", 3))
        if rating < 1 or rating > 5:
            return JsonResponse({"error": "Rating must be between 1 and 5."}, status=400)

        # get or create profile
        profile, _ = Profile.objects.get_or_create(
            full_name=data['full_name'],
            email=data.get('email'),
            role=data['role']
        )

        # create review
        Review.objects.create(
            reviewer=user,
            profile=profile,
            rating=data.get('rating', 3),
            comment=data.get('comment', "")
        )
        
        return JsonResponse({"message": "Review submitted successfully."})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def get_profile(request, profile_id):
    
    profile = get_object_or_404(Profile, id=profile_id)

    reviews = Review.objects.filter(profile=profile).select_related("reviewer")
    
    profile_data = {
        "id": profile.id,
        "full_name": profile.full_name,
        "email": profile.email,
        "role": profile.role,
        "reviews": [
            {
                "id": review.id,
                "reviewer": review.reviewer.first_name + " " + review.reviewer.last_name,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for review in reviews
        ],
    }

    return JsonResponse(profile_data, safe=False)



def claim_profile(request):
    user_id = request.user_id
    
    data = json.loads(request.body)
    profile_id =  data['profile_id']
    try:
        user = User.objects.filter(id=user_id).first()
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