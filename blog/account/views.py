from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile
from .forms import  UserRegistrationForm, \
                   UserEditForm, ProfileEditForm
# # action
from actions.utils import create_action
from actions.models import Action


@login_required
def dashboard(request):
    image_list = Profile.objects.all()
    return render(request,
                  'account/dashboard.html',
                  {'section': 'dashboard',
                  'images' : image_list})


def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object but avoid saving it yet
            new_user = user_form.save(commit=False)
            # Set the chosen password
            new_user.set_password(
                user_form.cleaned_data['password'])
            # Save the User object
            new_user.save()
            # Create the user profile
            Profile.objects.create(user=new_user)
            create_action(new_user, 'has created an account')
            return render(request,
                          'account/register_done.html',
                          {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()
    return render(request,
                  'account/register.html',
                  {'user_form': user_form})


@login_required
def edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user,
                                 data=request.POST)
        profile_form = ProfileEditForm(
                                    instance=request.user.profile,
                                    data=request.POST,
                                    files=request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Error updating your profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    return render(request,
                  'account/edit.html',
                  {'user_form': user_form,
                   'profile_form': profile_form})


@login_required()
def user_delete(request, id):
    if request.method == 'POST':
        user = User.objects.get(id=id)
        # Verify that the logged-in user and the user to be deleted are the same
        if request.user == user:
            #Log out, delete data and return to blog list
            logout(request)
            user.delete()
            print('user delete:',id)
            return redirect("login")
        else:
            return HttpResponse("You do not have permission to delete operations")
    else:
        return HttpResponse("Only accept post requests。")

