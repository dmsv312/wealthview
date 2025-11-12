from rest_framework import serializers
from django.core.exceptions import *
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from rest_framework.fields import CurrentUserDefault
from dateutil.parser import parse
import re
from backtest.models import *
import pandas as pd

def all_fridays(_from, _to):
    return pd.date_range(start=_from, end=_to, freq='W-FRI').tolist()




class AssetPricesSerializer(serializers.ModelSerializer):

	close = serializers.SerializerMethodField('get_close')

	

	def get_close(self, obj):
		return obj.price_after_split

	class Meta:
		model = AssetsPrices
		fields = ('close', 'date')
		
		read_only_fields = (
            "id",
        )


def get_closest_price(obj, date):
	data = obj.prices.all()

	data = data.filter(date__lte=date).order_by("-date").first()

	return data.price_after_split

class AssetSerializer(serializers.ModelSerializer):
	
	name = serializers.SerializerMethodField('get_ticker')
	exchange = serializers.SerializerMethodField('get_exchange')
	prices = serializers.SerializerMethodField('get_prices')

	def get_ticker(self, obj):
		return obj.exchange_ticker

	def get_exchange(self, obj):
		return "{} ({})".format(obj.exchange.name, obj.exchange.code)

	def test_week(self, index, data, week):
		if index < 0:
			return None

		price = data[index]

		if price.date.weekday() == 4:
			return price
		elif price.date.weekday() > 4:
			return data[index - 1]

	




	def get_prices(self, obj):
		context = self.context

		data = obj.prices.all()

		period = context.get("period")


		if context.get('date_from', None):
			data = data.filter(date__gte=context.get('date_from'))


		if context.get('date_to', None):
			data = data.filter(date__lte=context.get('date_to'))

		data = data.order_by("date")

		prices = []

		if period != "d" and period != "w":

			if period == "w":
				form = "%Y-%U"

			elif period == "m":
				form = "%Y-%m"

			elif period == "y":
				form = "%Y"

			weeks = {}
			for index, price in enumerate(data):
				
				week = price.date.strftime(form)

				if not weeks.get(week, None):
					week_list = []
				else:
					week_list = weeks.get(week)

				week_list.append(price)

				weeks[week] = week_list

			for week in weeks.items():
				prices.append(week[1][-1])
		else:
			prices = data


		if period == "w" and data.count():
			if context.get('date_from', None):
				date_from = context.get('date_from')
			else:
				date_from = data.first().date

			if context.get('date_to', None):
				date_to = context.get('date_to')
			else:
				date_to = data.last().date

			new_prices = []


			fridays = all_fridays(date_from, date_to)
			for friday in fridays:
				new_price = []
				new_price = AssetsPrices()
				new_price.date = friday.date()
				new_price.price_after_split = get_closest_price(obj, new_price.date)
				new_prices.append(new_price)

			prices = new_prices

				




		return AssetPricesSerializer(prices, many=True, context=context).data


	class Meta:
		model = Asset
		fields = ('name', 'exchange', 'prices')
		
		read_only_fields = (
            "id",
        )