from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from account.models import Profile, Portfolio


class Command(BaseCommand):

	def __init__(self):
		BaseCommand.__init__(self)

	help = 'Create profiles instances and default portfolio for users without this data'

	def handle(self, *args, **options):
		
		users = User.objects.all()
		for user in users:
			if not Profile.objects.filter(user=user).exists():
				profile = Profile.objects.create(user=user)
				Portfolio.objects.create(profile=profile, **Portfolio.get_default_settings())