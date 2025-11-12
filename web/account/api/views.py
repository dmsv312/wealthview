from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, UpdateModelMixin

from account.api.serializers import ProfileTelegramSerializer
from account.models import Profile


class ProfileTelegramViewset(ListModelMixin, GenericViewSet):
    model = Profile
    serializer_class = ProfileTelegramSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = Profile.objects.all()

    def get_object(self):
        return self.get_queryset().get()

    def get_queryset(self):
        return super().get_queryset().filter(tg_token=self.request.GET['tg_token'])

    @action(methods=['patch'], detail=False)
    def edit(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        Profile.objects.filter(tg_chat_id=profile.tg_chat_id).exclude(id=profile.id).update(
            tg_chat_id='', send_notify_dividends=False, send_notify_report_date=False
        )

        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def initial_data(self, request, *args, **kwargs):
        if request.GET.get('secret') != settings.BOT_SECRET or not request.GET.get('tg_chat_id'):
            return Response(status=404)
        qs = self.model.objects.filter(tg_chat_id=request.GET['tg_chat_id'])
        try:
            serializer = self.get_serializer(qs.get(), many=False)
        except self.model.DoesNotExist:
            return Response(status=404)
        return Response(serializer.data)
