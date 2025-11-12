from django.conf import settings


def environment(request):
    return {"IS_PRODUCTION": settings.ENVIRONMENT == "PRODUCTION"}
