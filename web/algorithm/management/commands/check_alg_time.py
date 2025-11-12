from django.core.management.base import BaseCommand as DjangoBaseCommand

from web.account.utils import timeit
from web.algorithm.mvp_personal_account import analysingPortfolio


class Command(DjangoBaseCommand):

    @timeit
    def handle(self, *args, **options):
        # # Тестовые входные параметры для анализа портфеля
        arrayCash_test = [['2018-01-31', 'United States Dollar', 'USD', 'Input', 10000]]

        # Массив обмена валюты (покупка / продажа)
        arrayChange_test = []

        # Массив транзакций инвестора
        arrayTickers_test = [['2018-01-31', 'Facebook', 'FB', 'NASDAQ', 'Buy', 185.67, 3],
                             ['2018-02-01', 'Apple', 'AAPL', 'NASDAQ', 'Buy', 167.88, 3],
                             ['2018-02-01', 'Visa', 'V', 'NYSE', 'Buy', 124.97, 8],
                             ['2018-02-12', 'Netflix', 'NFLX', 'NASDAQ', 'Buy', 255.24, 2],
                             ['2018-02-16', 'Facebook', 'FB', 'NASDAQ', 'Buy', 177.57, 3],
                             ['2018-02-21', 'Albemarle', 'ALB', 'NYSE', 'Buy', 113.94, 5],
                             ['2018-02-21', 'Starbucks', 'SBUX', 'NASDAQ', 'Buy', 56.5, 10],
                             ['2018-02-28', 'Albemarle', 'ALB', 'NYSE', 'Buy', 102.9, 5],
                             ['2018-03-14', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Buy', 75.1, 8],
                             ['2018-03-19', 'Facebook', 'FB', 'NASDAQ', 'Buy', 171.79, 3],
                             ['2018-03-19', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Buy', 70.41, 8],
                             ['2018-03-19', 'Albemarle', 'ALB', 'NYSE', 'Buy', 96.2, 5],
                             ['2018-03-26', 'Micron', 'MU', 'NASDAQ', 'Buy', 54.73, 10],
                             ['2018-03-26', 'Boeing', 'BA', 'NYSE', 'Buy', 327.29, 2],
                             ['2018-04-25', 'Micron', 'MU', 'NASDAQ', 'Buy', 47.45, 10],
                             ['2018-04-25', 'Square', 'SQ', 'NYSE', 'Buy', 44.71, 12],
                             ['2018-05-02', 'Square', 'SQ', 'NYSE', 'Buy', 49.40, 12],
                             ['2018-07-23', 'Square', 'SQ', 'NYSE', 'Sell', 71.71, 24],
                             ['2018-07-24', 'Boeing', 'BA', 'NYSE', 'Sell', 356.68, 2],
                             ['2018-07-24', 'Facebook', 'FB', 'NASDAQ', 'Sell', 213.6, 9],
                             ['2018-07-24', 'Apple', 'AAPL', 'NASDAQ', 'Sell', 192.83, 3],
                             ['2018-08-07', 'Albemarle', 'ALB', 'NYSE', 'Buy', 93.21, 5],
                             ['2018-08-30', 'Electronic Arts', 'EA', 'NASDAQ', 'Buy', 116.41, 5],
                             ['2018-09-11', 'Micron', 'MU', 'NASDAQ', 'Buy', 43.46, 15],
                             ['2018-09-12', 'Facebook', 'FB', 'NASDAQ', 'Buy', 161.98, 5],
                             ['2018-09-28', 'Facebook', 'FB', 'NASDAQ', 'Buy', 167.67, 5],
                             ['2018-10-16', 'Netflix', 'NFLX', 'NASDAQ', 'Buy', 338.32, 2],
                             ['2018-10-16', 'Electronic Arts', 'EA', 'NASDAQ', 'Buy', 107.59, 5],
                             ['2018-10-17', 'Square', 'SQ', 'NYSE', 'Buy', 76.71, 8],
                             ['2018-11-08', 'Starbucks', 'SBUX', 'NASDAQ', 'Sell', 68.75, 10],
                             ['2018-11-12', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Buy', 54.26, 13],
                             ['2019-02-05', 'Netflix', 'NFLX', 'NASDAQ', 'Sell', 356.56, 4],
                             ['2019-05-08', 'Albemarle', 'ALB', 'NYSE', 'Buy', 72.84, 8],
                             ['2019-07-24', 'Facebook', 'FB', 'NASDAQ', 'Sell', 201.17, 10],
                             ['2019-08-02', 'Square', 'SQ', 'NYSE', 'Buy', 68.5, 8],
                             ['2019-08-09', 'Valero Energy', 'VLO', 'NYSE', 'Buy', 79.1, 10],
                             ['2019-09-10', 'Square', 'SQ', 'NYSE', 'Buy', 61.23, 10],
                             ['2019-09-10', 'CVS Health', 'CVS', 'NYSE', 'Buy', 63.05, 5],
                             ['2020-04-20', 'Valero Energy', 'VLO', 'NYSE', 'Buy', 51.98, 11],
                             ['2020-06-03', 'Micron', 'MU', 'NASDAQ', 'Sell', 48.09, 35],
                             ['2020-06-03', 'Albemarle', 'ALB', 'NYSE', 'Sell', 79.72, 28],
                             ['2020-06-03', 'Square', 'SQ', 'NYSE', 'Sell', 90.88, 26],
                             ['2020-06-03', 'Electronic Arts', 'EA', 'NASDAQ', 'Sell', 118.65, 10],
                             ['2020-06-03', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Sell', 70.17, 29],
                             ['2020-06-03', 'CVS Health', 'CVS', 'NYSE', 'Sell', 66.68, 5],
                             ['2020-06-03', 'Valero Energy', 'VLO', 'NYSE', 'Sell', 69.32, 21],
                             ['2020-06-03', 'Visa', 'V', 'NYSE', 'Sell', 196.25, 8]]

        # Массив дивидендов активов инвестора
        arrayDividends_test = [['2018-02-15', 'Facebook', 'FB', 'NASDAQ', 'Dividend', 3.67, 3],
                               ['2018-02-15', 'Netflix', 'NFLX', 'NASDAQ', 'Dividend', 6.24, 2]]

        forexTr_test = "USD"
        benchTicker_test, benchExchange_test = "GSPC", "INDX"
        nonRiskTicker_test, nonRiskExchange_test = "IDCOT10TR", "INDX"
        startDateCurve_test, endDateCurve_test = 'None', 'None'

        test = analysingPortfolio(arrayTickers_test, arrayCash_test, arrayChange_test, arrayDividends_test,
                                  benchTicker_test, benchExchange_test,
                                  nonRiskTicker_test, nonRiskExchange_test,
                                  forexTr_test, startDateCurve_test, endDateCurve_test)

