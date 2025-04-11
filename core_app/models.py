from django.db import models

# Create your models here.
class User(models.Model):
    ROLE_CHOICES = [
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
    ]
    first_name = models.TextField(null=False)
    last_name = models.TextField(null=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255, blank=True, null=True)  # Store hashed passwords for credentials login
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    facebook_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    access_token = models.TextField(null=True)
    picture = models.TextField(null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    verified = models.BooleanField(default=False)  # If ID verification is needed

    # USERNAME_FIELD = "email"
    # REQUIRED_FIELDS = ["username"]
    

class Profile(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10, choices=User.ROLE_CHOICES)
    is_claimed = models.BooleanField(default=False)
    claimed_by = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Address fields
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)  # For display purposes

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    def save(self, *args, **kwargs):
        # Auto-generate location string if address fields exist
        if self.city and self.state:
            self.location = f"{self.city}, {self.state}"
        super().save(*args, **kwargs)


class Review(models.Model):
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Who wrote the review. Null for anonymous
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="reviews")  # Who the review is about
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 rating
    comment = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ProfileClaimRequest(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)  # If rejected


class ProfileClaimDispute(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    claimant = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("resolved", "Resolved"), ("rejected", "Rejected")],
        default="pending"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)