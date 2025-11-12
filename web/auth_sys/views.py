import uuid

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from account.models import Profile
from core.views import catch_error
from .email import send_registration_email, send_forget_password_email
from .tokens import account_activation_token


@catch_error
def login_user(request):
    user = request.user
    if user.is_authenticated:
        return redirect("/")
    else:
        args = {}
        args['process'] = "login"
        if request.POST:
            u_login = request.POST['login']
            password = request.POST['password']

            # Try to auth user
            user = authenticate(request, username=u_login, password=password)
            if user is not None:
                login(request, user)
                return redirect(request.GET.get('next', '/account'))
            else:
                args['login_error'] = "Неверный email или пароль. Повторите попытку."

        return render(request, 'auth_sys/login_page.html', args)


@catch_error
def logout_user(request):
    logout(request)
    return redirect('/')


@catch_error
def signup_user(request):
    user = request.user
    if user.is_authenticated:
        return redirect("/")

    args = {}
    args['process'] = "signup"
    args['success'] = False

    if request.POST:
        args['process'] = "activate"
        args['user_active'] = False
        username = str(uuid.uuid4().hex)
        email = str(request.POST['email']).lower().strip()
        password = request.POST['password']

        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(username=username, email=email, password=password, is_active=False)
            send_registration_email(request, user, password)
        else:
            raise NotImplementedError()  # TODO отдать ошибку формы

    return render(request, 'auth_sys/login_page.html', args)


@catch_error
def activate(request, uidb64, token):
    args = {}

    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        new_user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        new_user = None

    if new_user is not None and account_activation_token.check_token(new_user, token):
        new_user.is_active = True
        new_user.save()
        args['process'] = "activate"
        args['user_active'] = True

        new_profile = Profile.objects.create(user=new_user)

        return render(request, 'auth_sys/login_page.html', args)
    else:
        return redirect('/')


@catch_error
def forget_password(request):
    user = request.user
    if user.is_authenticated:
        return redirect("/")

    args = {}

    if request.POST:
        args['process'] = "forget_password"
        email = request.POST['email']
        user = User.objects.get(email__iexact=email)

        send_forget_password_email(request, email, user)

    return render(request, 'auth_sys/login_page.html', args)
