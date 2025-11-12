import datetime
import logging
from uuid import uuid4

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.utils import timezone

logger = logging.getLogger('logstash')


class LoginRequiredMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_anonymous and request.path.startswith('/account/') and resolve(request.path).url_name != 'change_password':
            return redirect(reverse('login') + '?next=' + request.path)

        response = self.get_response(request)

        return response


class RequestLoggerMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def log(self, request, response):
        now = timezone.now()
        request.request_uuid = str(uuid4().hex)
        response_time = (datetime.datetime.now() - self.started_at).total_seconds()
        user_id = request.user.id if request.user.is_authenticated else None
        user_id_verbose = user_id or 'anonymous'
        logger.info(f'{user_id_verbose} - {request.method} {request.path}', extra={
            'user_id': user_id,
            'host': request.get_host(),
            'http_host': request.META.get('HTTP_HOST', ''),
            'http_client_ip': request.META.get('HTTP_X_FORWARDED_FOR', ''),
            'request_full_path': request.get_full_path(),
            'request_at': now.isoformat(),
            'request_uuid': request.request_uuid,
            'request_method': request.method,
            'request_path': request.path,
            'request_data': {
                'get': request.GET,
                'post': request.POST,
            },
            'response_status_code': response.status_code,
            'response_time': response_time
        })

    def __call__(self, request):
        self.started_at = datetime.datetime.now()
        response = self.get_response(request)

        if settings.REQUESTS_LOG_ENABLED and '/staticfiles/' not in request.path and '/media/' not in request.path:
            self.log(request, response)

        return response
