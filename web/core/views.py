import functools
import traceback
import logging

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views import generic

JSON_DUMPS_PARAMS = {
    'ensure_ascii': False
}
TEMPLATE_ANALYZE = "error/error.html"

logger = logging.getLogger('wealthview')


class ErrorProcessingHelper:

    @staticmethod
    def ret(json_object, status=200):
        """Подготовка корректного ответа для браузера"""
        return JsonResponse(
            json_object,
            status=status,
            safe=not isinstance(json_object, list),
            json_dumps_params=JSON_DUMPS_PARAMS
        )

    @staticmethod
    def prepare_api_error_response(exception: Exception):
        """Формирование ответа с ошибкой"""
        result = {"errorMessage": str(exception)}
        return ErrorProcessingHelper.ret(result, status=400)

    @staticmethod
    def prepare_error_response(exception: Exception):
        """Формирование ответа с ошибкой"""
        result = {"errorMessage": str(exception),
                  "traceback": traceback.format_exc()}
        return ErrorProcessingHelper.ret(result, status=400)

    @staticmethod
    def process_error(ex, request, is_api_error=False):

        if settings.ENVIRONMENT != "LOCAL":
            logger.exception(ex)

        if settings.DEBUG:
            return ErrorProcessingHelper.prepare_error_response(ex)
        else:
            return (render(request, TEMPLATE_ANALYZE), ErrorProcessingHelper.prepare_api_error_response(ex))[is_api_error]


class BaseCatchErrorView(generic.View):
    """Базовый класс для всех вьюшек обрабатывает исключения"""

    def dispatch(self, request, *args, **kwargs):

        try:
            response = super().dispatch(request, *args, **kwargs)
        except Exception as ex:
            response = ErrorProcessingHelper.process_error(ex, request)

        if isinstance(response, (dict, list)):
            return self._response(response)
        else:
            return response

    @staticmethod
    def _response(data, *, status=200):
        return JsonResponse(
            data,
            status=status,
            safe=not isinstance(data, list),
            json_dumps_params=JSON_DUMPS_PARAMS
        )


def catch_error(fn):
    """Декоратор для обработки ошибок во всех views"""
    @functools.wraps(fn)
    def inner(request, *args, **kwargs):
        try:
            return fn(request, *args, **kwargs)
        except Exception as ex:
            return ErrorProcessingHelper.process_error(ex, request)

    return inner


def catch_api_error(fn):
    """Декоратор для обработки ошибок во всех запросов к Api"""
    @functools.wraps(fn)
    def inner(request, *args, **kwargs):
        try:
            return fn(request, *args, **kwargs)
        except Exception as ex:
            return ErrorProcessingHelper.process_error(ex, request, True)

    return inner



