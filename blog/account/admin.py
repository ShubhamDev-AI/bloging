from django.contrib import admin
from .models import Profile,Blocked


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'photo','bio']

@admin.register(Blocked)
class BlockedUser(admin.ModelAdmin):
    list_display = ['blocked_user']
