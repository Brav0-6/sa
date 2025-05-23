from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal to create or update user profile when a user is saved
    """
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Only save the profile if it exists
        try:
            if hasattr(instance, 'profile'):
                instance.profile.save()
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            UserProfile.objects.create(user=instance)
