from django.core.management.base import BaseCommand
from backtest.models import Asset
from django.utils import timezone

from django.db.models import Q


class Command(BaseCommand):

    def __init__(self):
        BaseCommand.__init__(self)

    help = 'Create profiles instances and default portfolio for users without this data'

    def handle(self, *args, **options):

        assets = Asset.objects.filter(
            Q(fund_attributes_update_date__lt=timezone.now()) | Q(fund_attributes_update_date__isnull=True)
        )
        i = 0
        for asset in assets:
            if asset.exchange:
                asset.update_attributes()
            else:
                asset.status = -1
                asset.save()
            i += 1
            print(f"left - {len(assets) - i}")
