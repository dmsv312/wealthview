import datetime

from django.db.models import Q
from django.utils import timezone

from WealthView.bot import send_to_chat
from account.api.serializers import ProfileTelegramSerializer
from account.models import Profile

from WealthView.celery import app


@app.task
def bot_notify_reset():
    """
        выполняется каждый день в 10:00 по Москве для сброса даты последнего уведомления
        если вдруг оно было прислано в 15:00 по каким-то причинам(например внезапно обновился атрибут)
    """
    total = Profile.objects.update(
        send_notify_dividends_at=None, send_notify_report_date_at=None,
        send_daily_notify_dividends_at=None, send_daily_notify_report_date_at=None,
    )
    print('reset bot notification dates: %s' % total)


@app.task
def bot_notify():
    profiles_dividends = Profile.objects.filter(send_notify_dividends=True, send_notify_dividends_at__isnull=True)
    profiles_reports = Profile.objects.filter(send_notify_report_date=True, send_notify_report_date_at__isnull=True)

    profiles_daily_dividends = Profile.objects.filter(send_daily_notify_dividends=True, send_daily_notify_dividends_at__isnull=True)
    profiles_daily_reports = Profile.objects.filter(send_daily_notify_report_date=True, send_daily_notify_report_date_at__isnull=True)

    print('start bot notify with dividends profiles %s and reports profiles %s' % (
        profiles_dividends.count(), profiles_reports.count()
    ))

    print('start bot notify DAILY with dividends profiles %s and reports profiles %s' % (
        profiles_daily_dividends.count(), profiles_daily_reports.count()
    ))
    
    for profile in profiles_dividends:
        print('process profile %s' % profile)
        serializer = ProfileTelegramSerializer(profile)
        portfolios = serializer.data['portfolios']
        total_data = portfolios.get('total_data')
        if portfolios and total_data:
            all_dividends_text_one_day_remaining = total_data['all_dividends_text_one_day_remaining']
            if all_dividends_text_one_day_remaining:
                print('process profile send dividends to %s' % profile)
                send_to_chat(profile.tg_chat_id, all_dividends_text_one_day_remaining)
                profile.send_notify_dividends_at = timezone.now()
                profile.save()

    for profile in profiles_daily_dividends:
        print('process profile %s' % profile)
        serializer = ProfileTelegramSerializer(profile)
        portfolios = serializer.data['portfolios']
        total_data = portfolios.get('total_data')
        if portfolios and total_data:
            all_dividends_text = total_data['all_dividends_text']
            if all_dividends_text:
                send_to_chat(profile.tg_chat_id, all_dividends_text)
                profile.send_daily_notify_dividends_at = timezone.now()
                profile.save()

    for profile in profiles_reports:
        print('process profile %s' % profile)
        serializer = ProfileTelegramSerializer(profile)
        portfolios = serializer.data['portfolios']
        total_data = portfolios.get('total_data')
        if portfolios and total_data:
            all_reports_text_one_day_remaining = total_data['all_reports_text_one_day_remaining']
            if all_reports_text_one_day_remaining:
                print('process profile send reports to %s' % profile)
                send_to_chat(profile.tg_chat_id, all_reports_text_one_day_remaining)
                profile.send_notify_report_date_at = timezone.now()
                profile.save()

    for profile in profiles_daily_reports:
        print('process profile %s' % profile)
        serializer = ProfileTelegramSerializer(profile)
        portfolios = serializer.data['portfolios']
        total_data = portfolios.get('total_data')
        if portfolios and total_data:
            all_reports_text = total_data['all_reports_text']
            if all_reports_text:
                send_to_chat(profile.tg_chat_id, all_reports_text)
                profile.send_daily_notify_report_date_at = timezone.now()
                profile.save()
