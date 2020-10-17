from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='profile')
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(upload_to='users/%Y/%m/%d/', blank=True)
    bio = models.TextField(max_length=500,blank=True)

    def __str__(self):
        return f'Profile for user {self.user.username}'

class Blocked(models.Model):
    blocked_user = models.OneToOneField(User, on_delete=models.CASCADE,related_name="blocked_users")
    blocked_by = models.ManyToManyField(User, related_name="blocked_by" )


