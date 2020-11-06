from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Profile
from .forms import  UserRegistrationForm, \
                   UserEditForm, ProfileEditForm,ProfileUploadForm
# # action
from actions.utils import create_action
from actions.models import Action
from django.views import View
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text, DjangoUnicodeDecodeError
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.template.loader import render_to_string
from .utils import account_activation_token
from django.urls import reverse
from django.contrib import auth
import json
from django.http import JsonResponse


@login_required
def dashboard(request):
    print(request.user.id)
    image_list = Profile.objects.all()
    return render(request,
                  'account/dashboard.html',
                  {'section': 'dashboard',
                  'images' : image_list})

def ProfileUpload(request):
    form_class = ProfileUploadForm
    form = form_class(request.POST or None,request.FILES or None)
    if request.method == 'POST':
        # A comment was posted
        if form.is_valid():
            title =form.data['user']
            # avatar = form.data['avatar']
            # print(avatar)
            form.save()
            return render(request,'account/dashboard.html',{'title':title})
    else:
        forms = ProfileUploadForm()
    return render(request,'account/dashboard.html',{'forms':forms})



# def register(request):
#     if request.method == 'POST':
#         user_form = UserRegistrationForm(request.POST)
#         if user_form.is_valid():
#             # Create a new user object but avoid saving it yet
#             new_user = user_form.save(commit=False)
#             # Set the chosen password
#             new_user.set_password(
#                 user_form.cleaned_data['password'])
#             # Save the User object
#             new_user.save()
#             # Create the user profile
#             Profile.objects.create(user=new_user)
#             create_action(new_user, 'has created an account')
#             return render(request,
#                           'account/register_done.html',
#                           {'new_user': new_user})
#     else:
#         user_form = UserRegistrationForm()
#     return render(request,
#                   'account/register.html',
#                   {'user_form': user_form})

# ----------------------- register -----------------------------------------
class RegistrationView(View):
    def get(self, request):
        return render(request, 'account/register.html')

    def post(self, request):
        # GET USER DATA
        # VALIDATE
        # create a user account

        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password =request.POST['confirm_password']

        context = {
            'fieldValues': request.POST
        }

        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if password != confirm_password:
                    if len(password) < 6:
                        messages.error(request, 'Password too short')
                        return render(request, 'account/register.html', context)
                    messages.error(request, 'Password Not Match')
                    return render(request, 'account/register.html', context)

                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()
                Profile.objects.create(user=user)

                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                               'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://'+current_site.domain+link

                email = EmailMessage(
                    email_subject,
                    'Hi '+user.username + ', Please the link below to activate your account \n'+activate_url,
                    'shubhamzade10055@gmail.com',
                    [email],
                )
                email.send(fail_silently=False)
                messages.success(request, 'Account successfully created')
                return render(request, 'account/register.html')

        return render(request, 'account/register.html')

# ----------------------- end register --------------------------------------
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

class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'email_error': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': 'sorry email in use,choose another one '}, status=409)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'username_error': 'username should only contain alphanumeric characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'sorry username in use,choose another one '}, status=409)
        return JsonResponse({'username_valid': True})

class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('login'+'?message='+'User already activated')

            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.Profile.signup_confirmation = True
            user.save()

            messages.success(request, 'Account activated successfully')
            return redirect('login')

        except Exception as ex:
            pass

        return redirect('login')




