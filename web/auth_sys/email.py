from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from auth_sys.tokens import account_activation_token


def send_registration_email(request, user, password):
    html_content = render_to_string('auth_sys/acc_active_email.html', {
        'username': user.username,
        'password': password,
        'email': user.email,
        'domain': request.get_host(),
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    msg = EmailMultiAlternatives('Регистрация в WealthView', '', settings.EMAIL_HOST_USER, [user.email])
    msg.attach_alternative(html_content, "text/html")
    if settings.IS_LOCAL_ENVIRONMENT:
        print(msg)
    else:
        msg.send(fail_silently=False)


def send_forget_password_email(request, email, user):
    html_content = render_to_string('auth_sys/restore_password.html', {
        'username': user.username,
        'email': email,
        'domain': request.get_host(),
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    subject = 'Восстановление пароля'
    msg = EmailMultiAlternatives(subject, '', settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    if settings.IS_LOCAL_ENVIRONMENT:
        print(msg)
    else:
        msg.send(fail_silently=False)


def send_change_password_mail(request, user):
    html_content = render_to_string('auth_sys/change_password.html', {
        'username': user.username,
        'email': user.email,
        'domain': request.get_host(),
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    subject = 'Смена пароля'
    msg = EmailMultiAlternatives(subject, '', settings.EMAIL_HOST_USER, [user.email])
    msg.attach_alternative(html_content, "text/html")
    if settings.IS_LOCAL_ENVIRONMENT:
        print(msg)
    else:
        msg.send(fail_silently=False)
