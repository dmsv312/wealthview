from rest_framework import viewsets, mixins
from backtest.models import *
from rest_framework.permissions import *
from .serializers import *
import dateutil.parser
from rest_framework.response import Response
from rest_framework.decorators import action
from handy.decorators import *
import json

class AssetViewset(mixins.CreateModelMixin, 
                   mixins.RetrieveModelMixin, 
                   mixins.UpdateModelMixin,
                   viewsets.GenericViewSet):
    queryset = Asset.objects.all()

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'register':
            permission_classes = []
        elif self.action == 'login':
            permission_classes = []
        elif self.action == 'checktoken':
            permission_classes = []
        elif self.action == 'options':
            permission_classes = []
        else:
            permission_classes = []
       
        return [permission() for permission in permission_classes]

    serializer_class = AssetSerializer

    

    @render_to_json()
    def list(self, request):
    	tickers = request.GET.get('tickers', None)
    	exchanges = request.GET.get('exchanges', None)
    	date_from = request.GET.get('date_from', "1900-01-01")
    	date_to = request.GET.get('date_to', None)
    	period = request.GET.get('period', "d")

    	if date_from:
    		try:
    			date_from = dateutil.parser.parse(date_from)
    		except:
    			return Response({"error": "Date from must be in YYYY-MM-DD format"}, status=403)

    	if date_to:
    		try:
    			date_to = dateutil.parser.parse(date_to)
    		except:
    			return Response({"error": "Date to must be in YYYY-MM-DD format"}, status=403)



    	if not tickers:
    		return Response({"error": "Tickers must be set"}, status=403)
    	else:
    		tickers = tickers.split(",")
    	

    	
    	test_assets = Asset.objects.filter(exchange_ticker__in=tickers)

    	arr = []
    	_min = None

    	for ass in test_assets:
    		first = AssetsPrices.objects.filter(asset__id=ass.id).order_by("date").first()
    		if first:
    			arr.append(first.date)

    	if len(arr):
    		_min = max(arr)




    	assets = Asset.objects.prefetch_related('prices').select_related('exchange').filter(exchange_ticker__in=tickers)

    	if exchanges:
    		exchanges = exchanges.split(",")
    		assets = assets.filter(exchange__code__in=exchanges)

    	if _min and _min > date_from.date():
    		date_from = _min




    	return AssetSerializer(assets, many=True, context={"date_from": date_from, "date_to": date_to, "period": period}).data