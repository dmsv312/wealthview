from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from core.views import catch_api_error


def is_email(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


@catch_api_error
def is_exist_username(request):
    if request.is_ajax():
        value = request.GET.get("username", None)
        if is_email(value):
            return JsonResponse({'is_taken': None})
        else:
            return is_exist_login(value, "username")
    else:
        return redirect(reverse("main-page"))


@catch_api_error
def is_exist_email(request):
    if request.is_ajax():
        value = request.GET.get("email", None)
        if is_email(value):
            return is_exist_login(value, "email")
        else:
            return JsonResponse({'is_taken': None})
    else:
        return redirect(reverse("main-page"))


def is_exist_login(value, field):
    data = {'is_taken': User.objects.filter(**{str(field) + "__iexact": value}).exists()}
    return JsonResponse(data)
