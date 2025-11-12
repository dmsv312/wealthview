from backtest.models import *
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from backtest.functions import parse

class Command(BaseCommand):

	def __init__(self):
		BaseCommand.__init__(self)

	help = 'Parse splits and prices for paticular ticker or all assets'

	def add_arguments(self, parser):
		parser.add_argument('ticker', nargs='+', type=str)

	def handle(self, *args, **options):

		
		ticker = options.get('ticker',None)

		if ticker:
			ticker = ticker[0]

		parse(ticker)


		
