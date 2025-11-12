import numpy as np
from scipy import stats

import asyncio

from datetime import datetime
from dateutil.relativedelta import relativedelta

# Подрузка необходимых функций для обработки данных
from .common_utils import days_in_range, weeks_in_range, search_date, forex_conversion, ln_estimator, alignment_prices

# Подгрузка модуля EOD
from .eod_service import main, get_url


def asset_estimator(asset_ticker, asset_exchange,
                    benchmark_ticker, benchmark_exchange,
                    risk_free_ticker, risk_free_exchange,
                    start_date, end_date, currency):
    """
    Расчёт статистических параметров каждого отдельного актива.
    :param asset_ticker: тикер актива
    :param asset_exchange: биржа актива
    :param benchmark_ticker: тикер бенчмарка
    :param benchmark_exchange: биржа бенчмарка
    :param risk_free_ticker: тикер безрисковой ставки
    :param risk_free_exchange: биржа безрисковой ставки
    :param start_date: начальная дата рассматриваемого периода
    :param end_date: конечная дата рассматриваемого периода
    :param currency: валюта анализа портфеля: USD или RUB
    :return: stats_metrics: показатели отдельного актива
    """

    # Недельные даты в рамках анализа портфеля в случае необработанных дат старта и конца анализа портфеля для ЛК
    all_weeks_in_range = weeks_in_range(start_date, end_date)
    weeks_analysis = len(all_weeks_in_range)

    if weeks_analysis < 30:
        return ""

    # Константные параметры
    rub_currency_ticker = 'RUB'  # Тикер валюты - Рубль
    usd_currency_ticker = 'USD'  # Тикер валюты - Доллар США
    usdrub_currency_ticker = 'USDRUB'  # Тикер курса валюты доллар-рубль
    currency_exchange = 'FOREX'  # Биржа курса валюты доллар-рубль
    ru_benchmark_tickers = ['IMOEX', 'MCFTR']  # Тикеры доступных бенчмарков РФ
    us_benchmark_tickers = ['SP500TR', 'GSPC', 'IXIC', 'NDX', 'ACWI', 'MSCIWORLD']  # Тикеры доступных бенчмарков США

    # Для избежания неккоретных обработок ошибок
    # Для этого вычитаем со стартовой даты анализа портфеля 5 дней (вполне достаточно) для запроса к eod_historical_data
    # Бывают случаи, что портфель начинается со вторника, а ближайшие цены закрытия бенчмарка были
    # в понедельник и среду, соответственно необходимо цену вторника заполнять ценой понедельника
    date_format = '%Y-%m-%d'  # Формат даты начала анализа портфеля
    start_date_url = datetime.strptime(start_date, date_format)
    start_date_url -= relativedelta(days=5)
    start_date_url = datetime.strftime(start_date_url, date_format)

    as_cnt = 0
    url_requests = []  # Формирование массива url-запросов финансовых данных к eod
    if asset_ticker not in [rub_currency_ticker, usd_currency_ticker]:  # Если в качестве актива Cash
        url_requests.append(get_url(asset_ticker, asset_exchange, start_date_url, end_date))
        as_cnt += 1

    url_requests.append(get_url(benchmark_ticker, benchmark_exchange, start_date_url, end_date))
    url_requests.append(get_url(risk_free_ticker, risk_free_exchange, start_date_url, end_date))

    # Условия добавления url-запроса курса валюты USDRUB
    currency_url_asset = get_url(usdrub_currency_ticker, currency_exchange, start_date_url, end_date)  # url-запрос USDRUB
    if asset_exchange == 'INDX':
        # Рассчитываем бенчмарк из США, но базовая валюта портфеля в рублях (RUB)
        if (asset_ticker in us_benchmark_tickers) and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        # Рассчитываем бенчмарк из РФ, но базовая валюта портфеля в долларах США (USD)
        if (asset_ticker in ru_benchmark_tickers) and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)
    elif asset_exchange == 'FOREX':
        # Для будущей конвертации денежных средств в валюту анализа портфеля
        if (asset_ticker == usd_currency_ticker) and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        if (asset_ticker == rub_currency_ticker) and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)
    else:
        # Рассчитываем актив из США, но базовая валюта портфеля в рублях (RUB)
        if (asset_exchange != 'MCX') and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        # Рассчитываем актив из РФ, но базовая валюта портфеля в долларах США (USD)
        if (asset_exchange == 'MCX') and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)

    # Для будущей конвертации бенчмарка в валюту анализа портфеля
    if url_requests[-1] != currency_url_asset:
        if (benchmark_ticker in us_benchmark_tickers) and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        if (benchmark_ticker in ru_benchmark_tickers) and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)

    # Для будущей конвертации безрисковой ставки в валюту анализа портфеля
    if url_requests[-1] != currency_url_asset:
        if (risk_free_ticker == 'IDCOT10TR') and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        if (risk_free_ticker == 'RGBITR') and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)

    # Формирование массива финансовых данных (цены закрытия активов, цены закрытия бенчмарка, цены курса валюты)
    finance_data = asyncio.run(main(url_requests))

    # Дата старта самого молодого актива (начала анализа портфеля), дата конца анализа портфеля
    start_asset_dates, end_asset_dates = [], []
    for i in range(len(url_requests)):
        try:
            start_asset_dates.append(finance_data[i][0]['date'])
            end_asset_dates.append(finance_data[i][-1]['date'])
        except IndexError:
            return "Выбранный актив должен существовать на всем периоде с " + \
                   start_date + " по " + end_date + " для проведения корректного анализа"

    start_asset_dates.append(start_date)
    start_analyze_date, end_analyze_date = max(start_asset_dates), min(end_asset_dates)

    # Для корректного расчёта GAGR портефля, бенчмарка, безрисковой ставки
    if end_date == datetime.strftime(datetime.today(), date_format):
        end_analyze_date = end_date

    if start_analyze_date > start_date:
        # Перевод дат в формат datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # Перевод дат в формат str
        start_date = datetime.strftime(start_date, '%d.%m.%Y')
        end_date = datetime.strftime(end_date, '%d.%m.%Y')
        return "Выбранный актив должен существовать на всем периоде с " + \
               start_date + " по " + end_date + " для проведения корректного анализа"

    # Работа с датами для рассчёта среднегодовой доходности
    start = datetime.strptime(start_analyze_date, '%Y-%m-%d')  # Начальная дата анализа портфеля (формат datetime)
    end = datetime.strptime(end_analyze_date, '%Y-%m-%d')  # Конечная дата анализа портфеля (формат datetime)
    diff_dates = relativedelta(end, start)  # Разность даты конца и даты начала
    months_cnt = diff_dates.years * 12 + diff_dates.months  # Количество полных месяцев анализируемого периода портфеля

    # Недельные даты в рамках анализа портфеля
    weekly_dates = weeks_in_range(start_analyze_date, end_analyze_date)
    weeks_analysis = len(weekly_dates)

    if weeks_analysis < 30:
        return ""

    # Дневные даты в рамках анализа портфеля
    daily_dates = days_in_range(start_analyze_date, end_analyze_date)
    days_analysis = len(daily_dates)

    # Формирование дневных цен закрытия актива, бенчмарка
    as_daily_prices = []
    bench_daily_dates, bench_daily_prices = [], []
    rf_daily_dates, rf_daily_prices = [], []
    for i in range(as_cnt + 2):
        dates, prices = [], []
        for j in range(len(finance_data[i])):
            dates = np.append(dates, finance_data[i][j]['date'])
            prices = np.append(prices, finance_data[i][j]['adjusted_close'])

        if i < as_cnt:
            as_daily_prices = alignment_prices(daily_dates, dates, prices)
        elif i == 1:
            bench_daily_dates, bench_daily_prices = daily_dates, alignment_prices(daily_dates, dates, prices)
        else:
            rf_daily_dates, rf_daily_prices = daily_dates, alignment_prices(daily_dates, dates, prices)

    # Формирование дневных цен курса валюты
    try:
        dates, prices = [], []
        for j in range(len(finance_data[as_cnt + 2])):
            dates = np.append(dates, finance_data[as_cnt + 2][j]['date'])
            prices = np.append(prices, finance_data[as_cnt + 2][j]['adjusted_close'])
        forex_daily_prices = alignment_prices(daily_dates, dates, prices)
    except IndexError:
        forex_daily_prices = np.ones(days_analysis)

    # Конвертация цен закрытия актива (индекса) в валюту анализа портфеля
    if asset_exchange == 'INDX':
        if (asset_ticker in us_benchmark_tickers) and (currency == rub_currency_ticker):
            as_daily_prices *= forex_daily_prices
        if (asset_ticker in ru_benchmark_tickers) and (currency == usd_currency_ticker):
            as_daily_prices /= forex_daily_prices

    # Конвертация и добавления цен денежных средств в валюту анализа портфеля
    elif asset_exchange == 'FOREX':
        if asset_ticker == usd_currency_ticker:
            if currency == usd_currency_ticker:  # Доллар США
                as_daily_prices = np.ones(days_analysis)
            else:  # Доллар США в Рублях
                as_daily_prices = np.ones(days_analysis) * forex_daily_prices

        if asset_ticker == rub_currency_ticker:
            if currency == rub_currency_ticker:  # Рубль РФ
                as_daily_prices = 100 * np.ones(days_analysis)
            else:  # Рубль РФ в долларах
                as_daily_prices = 100 * np.ones(days_analysis) / forex_daily_prices

    # Конвертация цен закрытия актива (акция, ETF) в валюту анализа портфеля
    else:
        as_daily_prices = forex_conversion(currency, asset_exchange, as_daily_prices, forex_daily_prices)


    # Для будущей конвертации бенчмарка в валюту анализа портфеля
    if (benchmark_ticker in us_benchmark_tickers) and (currency == rub_currency_ticker):
        bench_daily_prices *= forex_daily_prices
    if (benchmark_ticker in ru_benchmark_tickers) and (currency == usd_currency_ticker):
        bench_daily_prices /= forex_daily_prices

    # Для будущей конвертации безрисковой ставки в валюту анализа портфеля
    if (risk_free_ticker == 'IDCOT10TR') and (currency == rub_currency_ticker):
        rf_daily_prices *= forex_daily_prices
    if (risk_free_ticker == 'RGBITR') and (currency == usd_currency_ticker):
        rf_daily_prices /= forex_daily_prices

    # Нахождение дат для среднегодовой доходности (рассчитываем с точностью до месяца)
    ret_date = start + relativedelta(months=+ months_cnt)  # Конечная дата, после months_cnt месяцев существования портфеля
    ret_date = datetime.strftime(ret_date, '%Y-%m-%d')  # Перевод конечной даты в формат "строка"
    ret_ptf_date = search_date(daily_dates, ret_date, "-")  # Конечная среднегодовой доходности портфеля
    ret_bench_date = search_date(bench_daily_dates, ret_date, "-")  # Конечная среднегодовой доходности бенчмарка
    ret_rf_date = search_date(rf_daily_dates, ret_date, "-")  # Конечная среднегодовой доходности безрисковой ставки

    # Рассчёт недельных цен закрытия портфеля, курса валюты, бенчмарка
    asset_prices_weeks, forex_prices_weeks, bench_prices_weeks, ind_weeks = [], [], [], []
    for i in range(weeks_analysis):
        ind_days, = np.where(daily_dates == weekly_dates[i])[0]
        asset_prices_weeks = np.append(asset_prices_weeks, as_daily_prices[ind_days])
        bench_prices_weeks = np.append(bench_prices_weeks, bench_daily_prices[ind_days])
    asset_ln_weeks, bench_ln_weeks = ln_estimator(asset_prices_weeks), ln_estimator(bench_prices_weeks)

    # Среднегодовые доходности
    t_as, = np.where(np.array(daily_dates) == ret_ptf_date)[0]  # Среднегодовая доходность актива
    as_gagr = 100 * ((as_daily_prices[t_as] / as_daily_prices[0]) ** (12 / months_cnt) - 1)
    t_bench, = np.where(np.array(bench_daily_dates) == ret_bench_date)[0]  # Среднегодовая доходность бенчмакра
    bench_gagr = 100 * ((bench_daily_prices[t_bench] / bench_daily_prices[0]) ** (12 / months_cnt) - 1)
    t_rf, = np.where(np.array(rf_daily_dates) == ret_rf_date)[0]  # Среднегодовая доходность безрисковой ставки
    rf_gagr = 100 * ((rf_daily_prices[t_rf] / rf_daily_prices[0]) ** (12 / months_cnt) - 1)

    # Годовые параметры актива
    beta_asset = np.cov(asset_ln_weeks, bench_ln_weeks, bias=True)[0][1] / np.var(bench_ln_weeks)  # Бета-коэффициент
    alpha_asset = as_gagr - (rf_gagr + beta_asset * (bench_gagr - rf_gagr))  # Альфа-коэффициент
    vol_asset = np.std(asset_ln_weeks) * 52 ** (1 / 2)  # Волатильность актива

    # Коэффициент Шарпа, коэффициент корреляции бенчмарка и актива
    if vol_asset != 0:
        sharpe_asset = (as_gagr - rf_gagr) / vol_asset  # Коэффициент Шарпа
        corr_asset = 100 * stats.pearsonr(asset_ln_weeks, bench_ln_weeks)[0]  # Коэффициент корреляции портфеля и бенчмарка
    else:
        sharpe_asset = 0
        corr_asset = 0

    r_square_asset = 100 * (corr_asset / 100) ** 2  # Коэф.детерминации(R - квадрат)

    # Массив наименования параметров портфеля (names_ratio), массив значений параметров портфеля (array_ratio)
    names_ratio = np.array(['Доходность (GAGR)', 'Волатильность (σ)', 'Коэф. Шарпа (S)', 'Альфа (α)',
                            'Коэф. бета (β)', 'Коэф. корреляции', 'Коэфф. детерминации'])
    array_ratio = np.array([as_gagr, vol_asset, sharpe_asset, alpha_asset,
                            beta_asset, corr_asset, r_square_asset])
    unit_ratio = np.array(['%', '%', ' ', '%', ' ', '%', '%'])

    # Для вывода статистических параметров (коэффициентов портфеля) - объект dict()
    stats_metrics = np.zeros(7, dtype=object)
    for i in range(len(names_ratio)):
        stats_metrics[i] = dict()
        stats_metrics[i]['name'], stats_metrics[i]['value'] = names_ratio[i], array_ratio[i]
        stats_metrics[i]['unit'] = unit_ratio[i]

    return stats_metrics

# Для тестирования алгоритма
# ticker_test = 'AAPL'
# exchange_test = 'NASDAQ'
# s_date_test = '2020-01-01'
# e_date_test = '2020-12-21'
#
# test = asset_estimator(ticker_test, exchange_test, 'GSPC', 'INDX', 'IDCOT10TR', 'INDX', s_date_test, e_date_test, 'USD')
# print(test)
