from django.core.mail import send_mail

def send_notification(user, message):
    send_mail(
        "Profile Claim Update",
        message,
        "noreply@yourapp.com",
        [user.email],
        fail_silently=True
    )