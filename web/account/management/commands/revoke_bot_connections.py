from django.core.management.base import BaseCommand

from account.models import Profile


class Command(BaseCommand):

    def __init__(self):
        BaseCommand.__init__(self)

    help = 'remove chat_id from profiles and revoke all tg_token'

    def handle(self, *args, **options):

        # нельзя использовать update, так как не вызовется save() с генерацией токена
        for profile in Profile.objects.all():
            profile.tg_token = ''
            profile.tg_chat_id = ''
            profile.send_notify_dividends = False
            profile.send_notify_report_date = False
            profile.save()
