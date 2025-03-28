from django.utils.timezone import now
from core_app.models import Profile, ProfileClaimRequest, ProfileClaimDispute
from django.http import JsonResponse
from core_app.models import User
import json
from core_app.helpers.send_notifications import send_notification
from core_app.helpers.admin_required import admin_required

@admin_required  # Custom decorator to ensure only admins access this
def review_profile_claim(request):
    claim_id = request.data['claim_id']
    action = request.data['action']  # "approve" or "reject"
    rejection_reason = request.data.get('rejection_reason', '')

    claim = ProfileClaimRequest.objects.filter(id=claim_id, status="pending").first()
    if not claim:
        return JsonResponse({"error": "Claim not found or already reviewed."}, status=400)

    if action == "approve":
        claim.status = "approved"
        claim.profile.is_claimed = True
        claim.profile.claimed_by = claim.user
        claim.profile.save()
    elif action == "reject":
        claim.status = "rejected"
        claim.rejection_reason = rejection_reason

    claim.admin_reviewed_at = now()
    claim.save()

    # Notify the user
    send_notification(claim.user, f"Your claim request for {claim.profile.full_name} was {claim.status}.")

    return JsonResponse({"message": f"Claim {claim.status} successfully."})


@admin_required
def review_profile_dispute(request):
    data = json.loads(request.body)
    
    dispute_id = data['dispute_id']
    action = data['action']  # "resolve" or "reject"
    
    resolution_notes = request.data.get('resolution_notes', '')

    dispute = ProfileClaimDispute.objects.filter(id=dispute_id, status="pending").first()
    if not dispute:
        return JsonResponse({"error": "Dispute not found or already reviewed."}, status=400)

    if action == "resolve":
        # Reassign the profile to the claimant
        dispute.profile.claimed_by = dispute.claimant
        dispute.profile.save()

        # Reset previous claims
        ProfileClaimRequest.objects.filter(profile=dispute.profile).update(status="rejected")
    elif action == "reject":
        dispute.status = "rejected"

    dispute.admin_reviewed_at = now()
    dispute.resolution_notes = resolution_notes
    dispute.save()

    # Notify users
    send_notification(dispute.claimant, f"Your dispute for {dispute.profile.full_name} was {dispute.status}.")
    
    return JsonResponse({"message": f"Dispute {dispute.status} successfully."})


@admin_required
def get_pending_claims(request):
    claims = ProfileClaimRequest.objects.filter(status="pending").select_related("profile", "user")
    data = [{"id": c.id, "user": c.user.username, "profile": c.profile.full_name, "submitted_at": c.submitted_at} for c in claims]
    return JsonResponse(data)

@admin_required
def get_pending_disputes(request):
    disputes = ProfileClaimDispute.objects.filter(status="pending").select_related("profile", "claimant")
    data = [{"id": d.id, "claimant": d.claimant.username, "profile": d.profile.full_name, "submitted_at": d.submitted_at} for d in disputes]
    return JsonResponse(data)

