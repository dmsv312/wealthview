import numpy as np
from scipy import stats

import asyncio

from datetime import datetime
from dateutil.relativedelta import relativedelta

# Подрузка необходимых функций для обработки данных
from .common_utils import days_in_range, weeks_in_range, transpose, search_date, \
    forex_conversion, ln_estimator, alignment_prices

# Подгрузка модуля EOD
from .eod_service import main, get_url


def back_test_portfolio(tickers, exchanges, allocations, start_date, end_date,
                        benchmark_ticker, benchmark_exchange,
                        risk_free_ticker, risk_free_exchange,
                        currency, period_rebalance):
    """
    Функция бэк-теста портфеля.

    :param tickers: массив тикеров активов
    :param exchanges: массив бирж каждого актива
    :param allocations: массив аллокаций активов
    :param start_date: начальная дата анализа портфеля
    :param end_date: конечная дата анализа портфеля
    :param benchmark_ticker: тикер бенчмарка
    :param benchmark_exchange: биржа бенчмарка
    :param risk_free_ticker: тикер безрисковой ставки
    :param risk_free_exchange: биржа безрисковой ставки
    :param currency: валюта анализа портфеля: USD или RUB
    :param period_rebalance: период ребалансировки портфеля
    :return:
    """

    if np.sum(allocations) > 100: # Обработка исключения: сумма долей активов портфеля не может быть более 100 %
        return "Ошибка, пожалуйста попробуйте снова. Сумма долей активов должна быть не более 100 %"

    rub_currency_ticker = 'RUB'  # Тикер валюты - Рубль
    usd_currency_ticker = 'USD'  # Тикер валюты - Доллар США
    currency_ticker = 'USDRUB'  # Тикер курса валюты доллар-рубль
    currency_exchange = 'FOREX'  # Биржа курса валюты доллар-рубль

    # Проверка наличия текера RUB в массиве
    rub_allocation = 0
    if rub_currency_ticker in tickers:
        rub_index = tickers.index(rub_currency_ticker)
        rub_allocation = allocations[rub_index]
        del tickers[rub_index]
        del exchanges[rub_index]
        del allocations[rub_index]

    # Проверка наличия текера USD в массиве
    usd_allocation = 0
    if usd_currency_ticker in tickers:
        usd_index = tickers.index(usd_currency_ticker)
        usd_allocation = allocations[usd_index]
        del tickers[usd_index]
        del exchanges[usd_index]
        del allocations[usd_index]

    tickers_without_cash = tickers  # Тикеры без учёта cash
    as_cnt = len(tickers_without_cash)  # Количество активов в портфеле (без учёта cash)

    if usd_allocation != 0:
        tickers.append('USD')
        exchanges.append('FOREX')
        allocations.append(usd_allocation)

    if rub_allocation != 0:
        tickers.append('RUB')
        exchanges.append('FOREX')
        allocations.append(rub_allocation)

    tickers = np.array(tickers)
    exchanges = np.array(exchanges)
    allocations = np.array(allocations)

    url_requests = []  # Формирования массива url-запросов финансовых данных к eod
    for i in range(as_cnt):
        url_requests.append(get_url(tickers[i], exchanges[i], start_date, end_date))
    url_requests.append(get_url(benchmark_ticker, benchmark_exchange, start_date, end_date))
    url_requests.append(get_url(risk_free_ticker, risk_free_exchange, start_date, end_date))

    # url-запрос к курсу валюты доллар-рубль
    currency_url_asset = get_url(currency_ticker, currency_exchange, start_date, end_date)

    # Список бенчмарков, используемых в сервисе
    ru_benchmark_tickers = ['IMOEX', 'MCFTR']  # Тикеры доступных бенчмарков РФ
    us_benchmark_tickers = ['SP500TR', 'GSPC', 'IXIC', 'NDX', 'ACWI', 'MSCIWORLD']  # Тикеры доступных бенчмарков США

    # В портфеле содержатся активы из разных стран (РФ и США)
    if ('MCX' in exchanges) and (('NASDAQ' or 'NYSE ARCA' or 'NYSE' or 'BATS' or 'OTCQX') in exchanges):
        url_requests.append(currency_url_asset)
    # В портфеле содержатся ТОЛЬКО активы из США, но анализ портфеля в рублях (RUB)
    if ('MCX' not in exchanges) and (rub_allocation == 0) and (currency == rub_currency_ticker):
        url_requests.append(currency_url_asset)
    # В портфеле содержатся ТОЛЬКО активы из РФ, но анализ портфеля в долларах США (USD)
    if (('NASDAQ' or 'NYSE ARCA' or 'NYSE' or 'BATS' or 'OTCQX') not in exchanges) and (usd_allocation == 0) and (currency == usd_currency_ticker):
        url_requests.append(currency_url_asset)

    if url_requests[-1] != currency_url_asset:
        # Для будущей конвертации бенчмарка в валюту анализа портфеля
        if (benchmark_ticker in us_benchmark_tickers) and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        if (benchmark_ticker in ru_benchmark_tickers) and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)

    if url_requests[-1] != currency_url_asset:
        # Для будущей конвертации безрисковой ставки в валюту анализа портфеля
        if (risk_free_ticker == 'IDCOT10TR') and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        if (risk_free_ticker == 'RGBITR') and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)

    if url_requests[-1] != currency_url_asset:
        # Для будущей конвертации денежных средств в валюту анализа портфеля
        if (usd_allocation != 0) and (currency == rub_currency_ticker):
            url_requests.append(currency_url_asset)
        if (rub_allocation != 0) and (currency == usd_currency_ticker):
            url_requests.append(currency_url_asset)

    # Формирование массива финансовых данных (цены закрытия активов, цены закрытия бенчмарка, цены курса валюты)
    finance_data = asyncio.run(main(url_requests))

    # Дата старта самого молодого актива (начала анализа портфеля), дата конца анализа портфеля
    no_data_url_requests, start_no_data_dates = [], []
    start_asset_dates, end_asset_dates = [], []
    for i in range(len(url_requests)):
        try:
            start_asset_dates.append(finance_data[i][0]['date'])
            end_asset_dates.append(finance_data[i][-1]['date'])
        except IndexError:
            no_data_url_requests.append(url_requests[i].replace(end_date, '3000-01-01'))

    # Обработка отсутствия данных котировок (в случае если отсутствуют данные хотя-бы одной котировки)
    # Если отсутствуют данные 2 и более котировок, то рассматриваем большую начальную дату из них
    if len(no_data_url_requests) > 0:
        finance_data = asyncio.run(main(no_data_url_requests))
        for i in range(len(no_data_url_requests)):
            start_no_data_dates.append(finance_data[i][0]['date'])
        date_error = max(start_no_data_dates)
        date_error = datetime.strptime(date_error, '%Y-%m-%d')
        date_error = datetime.strftime(date_error, '%d.%m.%Y')
        return "Доступный период для анализа начинается с " + date_error

    start_analyze_date, end_analyze_date = max(start_asset_dates), min(end_asset_dates)

    # Для корректного расчёта GAGR портефля, бенчмарка, безрисковой ставки
    if end_date == datetime.strftime(datetime.today(), '%Y-%m-%d'):
        end_analyze_date = end_date

    # Работа с датами для рассчёта среднегодовой доходности
    start = datetime.strptime(start_analyze_date, '%Y-%m-%d')  # Начальная дата анализа портфеля (формат datetime)
    end = datetime.strptime(end_analyze_date, '%Y-%m-%d')  # Конечная дата анализа портфеля (формат datetime)
    diff_dates = relativedelta(end, start)  # Разность даты конца и даты начала
    months_cnt = diff_dates.years * 12 + diff_dates.months  # Количество полных месяцев анализируемого периода портфеля

    # Если рассматриваемый период анализа портфеля меньше 1 месяца
    if months_cnt == 0:
        min_start = start  # Минимально возможная стартовая дата анализа портфеля
        while min_start.weekday() in [5, 6]:
            min_start += relativedelta(days=1)
        min_start = datetime.strftime(min_start, '%d.%m.%Y')

        min_end = start + relativedelta(months=1)  # Минимально возможная конечная дата анализа портфеля
        while min_end.weekday() in [5, 6]:
            min_end += relativedelta(days=1)
        min_end = datetime.strftime(min_end, '%d.%m.%Y')
        return "Минимальный доступный период для анализа начинается с " + min_start + " по " + min_end

    # Дневные даты в рамках анализа портфеля
    all_days = days_in_range(start_analyze_date, end_analyze_date)
    days_analysis = len(all_days)

    # Формирование дневных цен закрытия активов, бенчмарка и безрисковой ставки
    as_close_days = np.zeros((as_cnt, days_analysis))
    bench_dates_days, bench_close_days, rf_dates_days, rf_close_days = [], [], [], []
    for i in range(as_cnt + 2):
        dates, prices = [], []
        for j in range(len(finance_data[i])):
            dates = np.append(dates, finance_data[i][j]['date'])
            prices = np.append(prices, finance_data[i][j]['adjusted_close'])

        if i < as_cnt:
            as_close_days[i] = alignment_prices(all_days, dates, prices)
        elif i == as_cnt:
            bench_dates_days, bench_close_days = all_days, alignment_prices(all_days, dates, prices)
        else:
            rf_dates_days, rf_close_days = all_days, alignment_prices(all_days, dates, prices)

    # Формирование дневных цен курса валюты
    try:
        forex_days, forex_dates = [], []
        for j in range(len(finance_data[as_cnt + 2])):
            forex_dates = np.append(forex_dates, finance_data[as_cnt + 2][j]['date'])
            forex_days = np.append(forex_days, finance_data[as_cnt + 2][j]['adjusted_close'])
        forex_close_days = alignment_prices(all_days, forex_dates, forex_days)
    except IndexError:
        forex_close_days = np.ones(days_analysis)

    # Цикл применения конвертации цен закрытия активов портфеля в валюту анализа портфеля
    for i in range(as_cnt):
        as_close_days[i] = forex_conversion(currency, exchanges[i], as_close_days[i], forex_close_days)

    # Конвертация и добавления цен денежных средств в валюту анализа портфеля
    if usd_allocation != 0:
        if currency == usd_currency_ticker:  # Доллар США
            as_close_days = np.append(as_close_days, [np.ones(days_analysis)], axis=0)
        else:  # Доллар США в Рублях
            as_close_days = np.append(as_close_days, [np.ones(days_analysis) * forex_close_days], axis=0)

    if rub_allocation != 0:
        if currency == rub_currency_ticker:  # Рубль РФ
            as_close_days = np.append(as_close_days, [100 * np.ones(days_analysis)], axis=0)
        else:  # Рубль РФ в долларах
            as_close_days = np.append(as_close_days, [100 * np.ones(days_analysis) / forex_close_days], axis=0)

    # Конвертация бенчмарка в валюту анализа портфеля
    if (benchmark_ticker in us_benchmark_tickers) and (currency == rub_currency_ticker):
        bench_close_days *= forex_close_days
    if (benchmark_ticker in ru_benchmark_tickers) and (currency == usd_currency_ticker):
        bench_close_days /= forex_close_days

    # Конвертация безрисковой ставки в валюту анализа портфеля
    if (risk_free_ticker == 'IDCOT10TR') and (currency == rub_currency_ticker):
        rf_close_days *= forex_close_days
    if (risk_free_ticker == 'RGBITR') and (currency == usd_currency_ticker):
        rf_close_days /= forex_close_days

    # Рассчёт начальной цены закрытия портфеля
    if currency == "USD":
        start_price = 10000
    else:
        start_price = 1000000

    tr_as_close_days, ptf_close_days = np.array(transpose(as_close_days)), []

    def rebalance_portfolio(share, asset_prices, all_dates_days, period, price0):

        share, days_cnt = np.array(share), len(all_dates_days)
        startDate, endDate = all_dates_days[0], all_dates_days[-1]
        startDate, endDate = datetime.strptime(startDate, '%Y-%m-%d'), datetime.strptime(endDate, '%Y-%m-%d')
        tempDate = startDate
        month, rebalancedDates = tempDate.month, []

        # Даты ежемесячной ребаланчировки портфеля
        if period == "month":
            tempDate = tempDate.replace(month=month, day=1) + relativedelta(months=1)
            while tempDate < endDate:
                tempDate = tempDate.replace(day=1)
                tempDate = datetime.strftime(tempDate, '%Y-%m-%d')
                tempDate = search_date(all_dates_days, tempDate, "+")
                rebalancedDates = np.append(rebalancedDates, tempDate)
                tempDate = datetime.strptime(tempDate, '%Y-%m-%d')
                tempDate += relativedelta(months=1)

        # Даты ежеквартальной ребалансировки портфеля
        if period == "quartal":
            if month in range(1, 4):
                month = 4
            elif month in range(4, 7):
                month = 7
            elif month in range(7, 10):
                month = 10
            else:
                month = 1

            tempDate = tempDate.replace(month=month, day=1)
            while tempDate < endDate:
                tempDate = tempDate.replace(day=1)
                tempDate = datetime.strftime(tempDate, '%Y-%m-%d')
                tempDate = search_date(all_dates_days, tempDate, "+")
                rebalancedDates = np.append(rebalancedDates, tempDate)
                tempDate = datetime.strptime(tempDate, '%Y-%m-%d')
                tempDate += relativedelta(months=3)

        # Даты полугодовой ребалансировки портфеля
        if period == "half_year":
            if month in range(1, 7):
                month = 7
            else:
                month = 1

            tempDate = tempDate.replace(month=month, day=1)
            while tempDate < endDate:
                tempDate = tempDate.replace(day=1)
                tempDate = datetime.strftime(tempDate, '%Y-%m-%d')
                tempDate = search_date(all_dates_days, tempDate, "+")
                rebalancedDates = np.append(rebalancedDates, tempDate)
                tempDate = datetime.strptime(tempDate, '%Y-%m-%d')
                tempDate += relativedelta(months=6)

        # Даты ежегодной ребалансировки портфеля
        if period == "year":
            month = 1

            tempDate = tempDate.replace(month=month, day=1) + relativedelta(years=1)
            while tempDate < endDate:
                tempDate = tempDate.replace(day=1)
                tempDate = datetime.strftime(tempDate, '%Y-%m-%d')
                tempDate = search_date(all_dates_days, tempDate, "+")
                rebalancedDates = np.append(rebalancedDates, tempDate)
                tempDate = datetime.strptime(tempDate, '%Y-%m-%d')
                tempDate += relativedelta(years=1)

        # Рассчёт цен закрытия портфеля с учётом его ребалансировки
        # Индекс в начальный момент времени / Количество каждого актива после ребалансировки
        # Цены закрытия портфеля с учётом его ребалансировки (rPtfCloseDays)
        r0, rPtfCloseDays = 0, []
        quality = price0 * share / (100 * asset_prices[0]) # Количество каждого актива
        rQual = quality
        for r_date in range(len(rebalancedDates)):
            r1, = np.where(all_dates_days == rebalancedDates[r_date])[0]
            for s in range(r0, r1):
                rPtfCloseDays = np.append(rPtfCloseDays, np.dot(rQual, asset_prices[s]))

            rQual = (share / (100 * asset_prices[r1])) * np.dot(rQual, asset_prices[r1])
            r0 = r1

        for s in range(r0, days_cnt):
            rPtfCloseDays = np.append(rPtfCloseDays, np.dot(rQual, asset_prices[s]))

        return rPtfCloseDays


    # Рассчёт цен закрытия портфеля с ребалансировкой и без неё
    if period_rebalance == 'None':
        qual = start_price * allocations / (100 * tr_as_close_days[0])  # Рассчёт количества каждого актива
        for i in range(days_analysis):  # Рассчёт цен закрытия портфеля - его доходностей
            ptf_close_days = np.append(ptf_close_days, np.dot(qual, tr_as_close_days[i]))
    else:
        ptf_close_days = rebalance_portfolio(allocations, tr_as_close_days, all_days, period_rebalance, start_price)

    # Функция рассчёта доходностей портфеля за произвольный период c iSDateP по iEDateP
    # !Примечание: данная функция используется для графика изменения доходностей портфеля
    # iSDateP - input start date period (дата начала произвольного периода доходностей портфеля)
    # iEDateP - input end date period (дата конца произвольного периода доходностей портфеля)
    def retPtfPeriod(iSDateP, iEDateP):
        # Формирование массива цен закрытия портфеля по дням с iSDateP по iEDateP
        sInd, = np.where(all_days == iSDateP)[0]  # Индекс начальной цены закрытия портфеля из всего массива
        eInd, = np.where(all_days == iEDateP)[0]  # Индекс конечной цены закрытия из всего массива
        ptfCloseDaysP, ptfDatesDaysP = [], []  # Даты, цены закрытия портфеля произвольного периода
        for pDays in range(sInd, eInd + 1):
            ptfDatesDaysP = np.append(ptfDatesDaysP, all_days[pDays])
            ptfCloseDaysP = np.append(ptfCloseDaysP, 100 * (np.dot(allocations / 100,
                                                                   tr_as_close_days[pDays] / tr_as_close_days[sInd]) - 1))
        return ptfDatesDaysP, ptfCloseDaysP

    # Нахождение дат для среднегодовой доходности (рассчитываем с точностью до месяца)
    return_date = start + relativedelta(months=+ months_cnt)  # Конечная дата, после months_cnt месяцев существования портфеля
    return_date = datetime.strftime(return_date, '%Y-%m-%d')  # Перевод конечной даты в формат "строка"
    retDatePtf = search_date(all_days, return_date, "-")  # Конечная среднегодовой доходности портфеля
    retDateBench = search_date(bench_dates_days, return_date, "-")  # Конечная среднегодовой доходности портфеля бенчмарка
    retDateNr = search_date(rf_dates_days, return_date, "-")  # Конечная среднегодовой доходности портфеля безрисковой ставки

    # Функция для рассчёта абсолютных показателей портфеля, бенчманка, безрисковой ставки
    def returnsPeriod(iEDate, iPeriod):
        if iPeriod == "All":
            retPtf = 100 * (ptf_close_days[-1] / ptf_close_days[0] - 1)
            retBench = 100 * (bench_close_days[-1] / bench_close_days[0] - 1)
            retNR = 100 * (rf_close_days[-1] / rf_close_days[0] - 1)
        else:
            if iPeriod == "YTD":
                thisYear = datetime.strftime(iEDate, '%Y')
                date1 = datetime(int(thisYear), 1, 1)
            else:
                end_ret = iEDate
                date1 = end_ret - relativedelta(months=+ iPeriod)

            date2 = datetime.strftime(date1, '%Y-%m-%d')

            datePtf = search_date(all_days, date2, "-")
            dateBench = search_date(bench_dates_days, date2, "-")
            dateNR = search_date(rf_dates_days, date2, "-")

            rpIndPtf, = np.where(all_days == datePtf)[0]
            rpIndBench, = np.where(bench_dates_days == dateBench)[0]
            rpIndNR, = np.where(rf_dates_days == dateNR)[0]

            retPtf = 100 * (ptf_close_days[-1] / ptf_close_days[rpIndPtf] - 1)
            retBench = 100 * (bench_close_days[-1] / bench_close_days[rpIndBench] - 1)
            retNR = 100 * (rf_close_days[-1] / rf_close_days[rpIndNR] - 1)

        retAs = np.array([retPtf, retBench, retNR])
        return retAs

    # Рассчёт показателей абсолютной доходности портфеля, бенчмарка
    # !В зависимости от периода существования портфеля
    if months_cnt < 3:
        retOneM, retAll = returnsPeriod(end, 1), returnsPeriod(end, "All")
        returnPtf = [retOneM[0], retAll[0]]
        returnBench = [retOneM[1], retAll[1]]
        returnNr = [retOneM[2], retAll[2]]
    elif 3 <= months_cnt < 6:
        retOneM, retThreeM, retAll = returnsPeriod(end, 1), returnsPeriod(end, 3), returnsPeriod(end, "All")
        returnPtf = [retOneM[0], retThreeM[0], retAll[0]]
        returnBench = [retOneM[1], retThreeM[1], retAll[1]]
        returnNr = [retOneM[2], retThreeM[2], retAll[2]]
    elif 6 <= months_cnt < 12:
        retOneM, retThreeM, retSixM = returnsPeriod(end, 1), returnsPeriod(end, 3), returnsPeriod(end, 6)
        retAll = returnsPeriod(end, "All")
        returnPtf = [retOneM[0], retThreeM[0], retSixM[0], retAll[0]]
        returnBench = [retOneM[1], retThreeM[1], retSixM[1], retAll[1]]
        returnNr = [retOneM[2], retThreeM[2], retSixM[2], retAll[2]]
    else:
        retOneM, retThreeM, retSixM = returnsPeriod(end, 1), returnsPeriod(end, 3), returnsPeriod(end, 6)
        retOneY, retAll = returnsPeriod(end, 12), returnsPeriod(end, "All")
        returnPtf = [retOneM[0], retThreeM[0], retSixM[0], retOneY[0], retAll[0]]
        returnBench = [retOneM[1], retThreeM[1], retSixM[1], retOneY[1], retAll[1]]
        returnNr = [retOneM[2], retThreeM[2], retSixM[2], retOneY[2], retAll[2]]

    # Рассчёт доходности YTD (в зависимости от старта года)
    if end.year - start.year > 0:
        retYTD = returnsPeriod(end, "YTD")
    else:
        retYTD = retAll

    returnPtf = np.insert(returnPtf, -1, retYTD[0])
    returnBench = np.insert(returnBench, -1, retYTD[1])
    returnNr = np.insert(returnNr, -1, retYTD[2])

    # Для вывода абсолютных показателей доходности портфеля, бенчмарка, безрисковой ставки
    return_array = np.array([returnPtf, returnBench, returnNr])

    # Недельные даты в рамках анализа портфеля
    all_weeks = weeks_in_range(start_analyze_date, end_analyze_date)
    weeks_analysis = len(all_weeks)

    # Если число недельных наблюдений менее 30, то параметры портфеля не подлежат расчёту (не возвращаем их)
    if weeks_analysis < 30:
        return tickers, exchanges, allocations, bench_dates_days, bench_close_days, rf_dates_days, rf_close_days, \
               all_days, ptf_close_days, return_array, tr_as_close_days

    # Рассчёт недельных цен закрытия портфеля, курса валюты, бенчмарка
    ptf_close_weeks, bench_close_weeks, indWeeks = [], [], []
    for w in range(weeks_analysis):
        ptfCloseIndDays, = np.where(all_days == all_weeks[w])
        indWeeks = np.append(indWeeks, ptfCloseIndDays[0])
        ptf_close_weeks = np.append(ptf_close_weeks, ptf_close_days[ptfCloseIndDays[0]])
        bench_close_weeks = np.append(bench_close_weeks, bench_close_days[ptfCloseIndDays[0]])

    # Логарифмы отношения цен бенчмарка недельных данных
    bench_ln_weeks = ln_estimator(bench_close_weeks)

    # Рассчёт недельных цен закрытия активов
    as_close_weeks, asset_ln_weeks = [[]] * as_cnt, [[]] * as_cnt
    for i in range(as_cnt):
        for w in range(weeks_analysis):
            as_close_weeks[i] = np.append(as_close_weeks[i], as_close_days[i][int(indWeeks[w])])

    # Рассчёт цен закрытия активов, логарифмов отношения цен активов (для рассчёта статистик)
    # !Примечание: сначала(!) цены закрытия активов конвертируем в валюту анализа портфеля
    for i in range(as_cnt):
        asset_ln_weeks[i] = ln_estimator(as_close_weeks[i])

    # Логарифмов отношения цен закрытия портфеля (недельные наблюдения)
    ptf_ln_weeks = ln_estimator(ptf_close_weeks)
    volatility_benchmark = np.std(bench_ln_weeks) * 52 ** (1 / 2)  # Волатильность Бенчмарка

    # Рассчёт волатильности и бета-коэффициентов каждого из активов портфеля
    if as_cnt == 0:
        tickers_and_bench = np.array([benchmark_ticker])  # Тикеры активов портфеля и бенчмарка
        vol_assets_bench = np.array([volatility_benchmark])  # Волатильности активов портфеля и бенчмарка
        beta_assets_bench = np.array([1])  # Бета-коэффициенты активов потрфеля и бенчмарка (он вегда равен 1)
        corr_matrix = [[1]]  # Корреляционная матрица активов портфеля и бенчмарка
    else:
        vol_assets, beta_assets = [], []
        tickers_and_bench = np.append(benchmark_ticker, tickers_without_cash)  # Тикеры активов портфеля и бенчмарка
        for i in range(as_cnt):
            vol_assets = np.append(vol_assets, np.std(asset_ln_weeks[i]) * 52 ** (1 / 2))
            beta_assets = np.append(beta_assets, np.cov(asset_ln_weeks[i], bench_ln_weeks, bias=True)[0][1] / np.var(bench_ln_weeks))
            vol_assets_bench = np.append(volatility_benchmark, vol_assets)  # Волатильности активов портфеля и бенчмарка
            beta_assets_bench = np.append(1, beta_assets)  # Бета-коэффициенты активов потрфеля и бенчмарка (он вегда равен 1)

        ln_prices = np.append([bench_ln_weeks], asset_ln_weeks, axis=0)  # Логарифмы отношения цен активов портфеля и бенчмарка
        corr_matrix = np.corrcoef(ln_prices)  # Корреляционная матрица активов портфеля и бенчмарка

    # Логарифмы отношения цен активов портфеля и бенчмарка    # Массив тикеров активов портфеля и бенчмарка, их волатильности и бета-коэффициенты
    tickers_vol_beta = np.array([tickers_and_bench, vol_assets_bench, beta_assets_bench])

    # Среднегодовые доходности портфеля/бенчмарка/безрисковой ставки
    ptfIndReturn, = np.where(np.array(all_days) == retDatePtf)  # Среднегодовая доходность портфеля
    portfolio_gagr = 100 * ((ptf_close_days[ptfIndReturn[0]] / ptf_close_days[0]) ** (12 / months_cnt) - 1)
    benchIndReturn, = np.where(np.array(bench_dates_days) == retDateBench)  # Среднегодовая доходность бенчмакра
    benchmark_gagr = 100 * ((bench_close_days[benchIndReturn[0]] / bench_close_days[0]) ** (12 / months_cnt) - 1)
    nrIndReturn, = np.where(np.array(rf_dates_days) == retDateNr)  # Среднегодовая доходность безрисковой ставки
    risk_free_gagr = 100 * ((rf_close_days[nrIndReturn[0]] / rf_close_days[0]) ** (12 / months_cnt) - 1)

    # Годовые параметры бенчмарка
    beta_benchmark = 1  # Бета-коэффициент
    alpha_benchmark = 0  # Альфа-коэффициент
    sharpe_benchmark = (benchmark_gagr - risk_free_gagr) / volatility_benchmark  # Коэффициент Шарпа
    corr_benchmark = 100  # Коэффициент корреляции портфеля и бенчмарка
    r_square_benchmark = 100 * (corr_benchmark / 100) ** 22  # Коэфициент детерминации (R - квадрат)

    # Годовые параметры портеля
    beta_portfolio = np.cov(ptf_ln_weeks, bench_ln_weeks, bias=True)[0][1] / np.var(bench_ln_weeks)  # Бета-коэффициент
    alpha_portfolio = portfolio_gagr - (risk_free_gagr + beta_portfolio * (benchmark_gagr - risk_free_gagr))  # Альфа-коэффициент
    volatility_portfolio = np.std(ptf_ln_weeks) * 52 ** (1 / 2)  # Волатильность

    # Коэффициент Шарпа, коэффициент корреляции бенчмарка и портфеля
    if volatility_portfolio != 0:
        sharpe_portfolio = (portfolio_gagr - risk_free_gagr) / volatility_portfolio  # Коэффициент Шарпа
        corr_portfolio = 100 * stats.pearsonr(ptf_ln_weeks, bench_ln_weeks)[0]  # Коэффициент корреляции портфеля и бенчмарка
    else:
        sharpe_portfolio = 0
        corr_portfolio = 0

    r_square_portfolio = 100 * (corr_portfolio / 100) ** 2  # Коэфициент детерминации (R - квадрат)

    # Вывод риск-профиля портфеля
    if volatility_portfolio < 5:
        r_profile_name, r_profile_num = 'Консервативный', 1
    elif 5 <= volatility_portfolio < 10:
        r_profile_name, r_profile_num = 'Умеренно-консервативный', 2
    elif 10 <= volatility_portfolio < 15:
        r_profile_name, r_profile_num = 'Умеренный', 3
    elif 15 <= volatility_portfolio < 20:
        r_profile_name, r_profile_num = 'Умеренно-агрессивный', 4
    else:
        r_profile_name, r_profile_num = 'Агрессивный', 5
    risk_profile = [r_profile_num, r_profile_name]  # Название риск-профиля, номер риск-профиля

    # Массивы: наименования параметров (names_ratio), значений параметров портфеля (portfolio_ratio),
    # значений параметров бенчмарка (benchmark_ratio), единиц измерения параметров (unit_ratio)
    names_ratio = np.array(['Доходность (GAGR)', 'Волатильность (σ)', 'Коэф. Шарпа (S)', 'Альфа (α)',
                            'Коэф. бета (β)', 'Коэф. корреляции', 'Коэфф. детерминации'])
    portfolio_ratio = np.array([portfolio_gagr, volatility_portfolio, sharpe_portfolio, alpha_portfolio,
                                beta_portfolio, corr_portfolio, r_square_portfolio])
    benchmark_ratio = np.array([benchmark_gagr, volatility_benchmark, sharpe_benchmark, alpha_benchmark,
                                beta_benchmark, corr_benchmark, r_square_benchmark])
    unit_ratio = np.array(['%', '%', ' ', '%', ' ', '%', '%'])

    # Для вывода статистических параметров (коэффициентов портфеля) - объект dict()
    stats_param = np.zeros(7, dtype=object)
    for i in range(len(names_ratio)):
        stats_param[i] = dict()
        stats_param[i]['name'], stats_param[i]['value_portfolio'] = names_ratio[i], portfolio_ratio[i]
        stats_param[i]['value_benchmark'], stats_param[i]['unit'] = benchmark_ratio[i], unit_ratio[i]

    return tickers, exchanges, allocations, bench_dates_days, bench_close_days, rf_dates_days, rf_close_days, \
           all_days, ptf_close_days, return_array, tr_as_close_days, stats_param, corr_matrix, tickers_vol_beta, risk_profile


# # Массивы для тестирования алгоритма
# allocations_test = [1] * 100
# tickers_test = ["SPY", "QQQ", "SBER", "LKOH", "GMKN", "PLZL", "MCHI", "SCHH", "AAPL", "ROSN"] * 10
# exchanges_test = ["NYSE ARCA", "NASDAQ", "MCX", "MCX", "MCX", "MCX", "NASDAQ", "NYSE ARCA", "NASDAQ", "MCX"] * 10

# allocations_test = [25, 25, 25, 25]
# tickers_test = ['AAPL', 'LKOH', 'GAZP', 'SBUX']
# exchanges_test = ['NASDAQ', 'MCX', 'MCX', 'NASDAQ']

# allocations_test = [15, 15, 7.50, 7.50, 7.50, 5, 10, 12.5, 10, 5]
# tickers_test = ["SPY", "QQQ", "SBER", "LKOH", "GMKN", "PLZL", "MCHI", "SCHH", "AAPL", "ROSN"]
# exchanges_test = ["NYSE ARCA", "NASDAQ", "MCX", "MCX", "MCX", "MCX", "NASDAQ", "NYSE ARCA", "NASDAQ", "MCX"]

# allocations_test = [1] * 100
# tickers_test = ["AAPL", "MU", "BAC", "WWW"] * 25
# exchanges_test = ["NASDAQ", "NASDAQ", "US", "US"] * 25

# allocations_test = [20] * 5
# tickers_test = ["TATN", "AAPL", "SBUX", "MU", "SPY"]
# exchanges_test = ["MCX", "NASDAQ", "NASDAQ", "NASDAQ", "NYSE ARCA"]

# tickers_test = ['IVV', 'TSLA', 'RUB', 'YNDX']
# exchanges_test = ['NYSE ARCA', 'NASDAQ', 'FOREX', 'NYSE']
# allocations_test = [25, 25, 25, 25]

# tickers_test = ['LKOH', 'SBER', 'RUB']
# exchanges_test = ['MCX', 'MCX', 'FOREX']
# allocations_test = [20, 20, 60]

# tickers_test = ['GBTC']
# exchanges_test = ['OTCQX']
# allocations_test = [100]
#
# answer = back_test_portfolio(tickers_test, exchanges_test, allocations_test, '2010-06-28', '2020-11-11',
#                            'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None')
#
# print(answer)
