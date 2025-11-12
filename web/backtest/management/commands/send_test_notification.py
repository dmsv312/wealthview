from django.core.management.base import BaseCommand

from WealthView.bot import send_dividends_notification, send_reports_notification
from account.models import Profile


class Command(BaseCommand):
	def handle(self, *args, **options):
		profile = Profile.objects.get(id=4)
		send_reports_notification(profile.tg_chat_id)
		send_dividends_notification(profile.tg_chat_id)

