import asyncio
from scipy import stats
import numpy as np

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Подрузка необходимых функций для обработки данных
from .common_utils import days_in_range, weeks_in_range, transpose, search_date, \
    forex_conversion, ln_estimator, alignment_prices

# Подгрузка модуля EOD
from .eod_service import main, get_split_data, get_url, get_live_url


# Функция, возвращающая доходности портфеля по дням с iDateStart по iDateEnd (с учётом пополнений-снятий!)
# Необходима для вывода графика доходностей портфеля
# iDateStart - input date start (входная начальная дата доходности портфеля)
# iDateEnd - input date end (входная конечная дата доходности портфеля)
# iArrayCash1 - input array cash Input/Output (входной массив транзакций инвестора - пополнение/снятие валют)
# iForexTr1 - input forex (в какой валюте будем анализировать портфель: USD или RUB)

# Вводные кэшируемые параметры
# iAllDays - соответствует allDays (все дни алазина портфеля)
# iPtfCloseDays - соответствует ptfCloseDays (цены закрытия портфеля по дням)
# iForexCloseDays - соответствует forexCloseDays (цены закрытия курса валют по дням)
# iSDate - соответствует sDate (дата старта анализа портфеля)
def returnsPortfolioPeriod(iArrayCash1, iForexTr1,
                           iAllDays, iPtfCloseDays, iForexCloseDays, iSDate,
                           iDateStart, iDateEnd):
    # Разбиваем массив пополнений/снятий валюты
    cashQtyOper1 = len(iArrayCash1)  # Количество операций инвестора с кэшэм (строк массива)
    if cashQtyOper1 == 0:
        iArrayCash1 = [[' ', ' ', ' ', ' ', 0]]

    trArrayCash1 = transpose(iArrayCash1)  # Транспонирование матрицы транзакций с кэшэм
    cashDatesOper1 = np.array(trArrayCash1[0])  # Даты каждой транзакции (пополнений или снятий)
    cashForex1 = np.array(trArrayCash1[2])  # Валюта каждой транзакции (пополнений или снятий)
    cashTypeOper1 = np.array(trArrayCash1[3])  # Тип транзакции (пополнить, снять)
    cashSum1 = np.array(trArrayCash1[4], dtype='float64')  # Сумма транзакции (на счету у нас доллары и рубли)

    # Перевод валюты пополнений-снятий в валюту анализа портфеля (с учётом курса на день пополнения-снятия)
    for cash in range(cashQtyOper1):
        index, = np.where(iAllDays == cashDatesOper1[cash])[0]
        if iForexTr1 == "USD" and cashForex1[cash] == "RUB":
            cashSum1[cash] /= iForexCloseDays[index]
        elif iForexTr1 == "RUB" and cashForex1[cash] == "USD":
            cashSum1[cash] *= iForexCloseDays[index]

    # Формирование массива цен закрытия портфеля по дням с iDateStart по iDateEnd
    perPtfCloseDays, perPtfCloseAbsDays, perUnqDatesDays, deltaIndex = [], [], [], 0
    if iDateStart == 'None' and iDateEnd == 'None':
        iDateStart, iDateEnd = iAllDays[0], iAllDays[-1]
        indStart = 0
        indEnd, = np.where(iAllDays == iAllDays[-1])[0]
    else:
        indStart, = np.where(iAllDays == iDateStart)[0]  # Индекс начальной цены закрытия портфеля из всего массива
        indEnd, = np.where(iAllDays == iDateEnd)[0]  # Индекс конечной цены закрытия из всего массива

    lengthPeriod = indEnd - indStart + 1  # Длина анализируемого периода (число дней)
    for pDays in range(indStart, indEnd + 1):
        perUnqDatesDays = np.append(perUnqDatesDays, iAllDays[pDays])
        perPtfCloseDays = np.append(perPtfCloseDays, iPtfCloseDays[pDays])
        deltaIndex += 1

    # Цикл рассчёта доходности портфеля по дням (с учётом пополнений и снятий) в диапазоне индексов
    # unqCashDatesOper - уникальные даты в массиве пополнений-снятий
    # unqCashQtyOper - количество уникальных дат в массиве пополнений-снятий
    # unqCashDatesOperPeriod - уникальные даты в массиве пополнений-снятий с учётом диапазона периода
    # unqCashQtyOperPeriod - количество уникальных дат в массиве пополнений-снятий с учётом диапазона периода
    unqCashDatesOper, unqCashDatesOperPeriod = np.unique(cashDatesOper1), []
    unqCashQtyOper, unqCashQtyOperPeriod = len(unqCashDatesOper), 0
    for uCash in range(unqCashQtyOper):
        if iDateStart <= unqCashDatesOper[uCash] <= iDateEnd:
            unqCashDatesOperPeriod = np.append(unqCashDatesOperPeriod, unqCashDatesOper[uCash])
            unqCashQtyOperPeriod += 1

    # Вектор весов (для рассчёта средневзвешенной суммы), средневзвешенная сумма
    timeVector, weightedS = [], 0

    if unqCashQtyOperPeriod == 0:  # Случай отсутствия пополнений-снятий в заданном нами диапазоне
        for pDay in range(lengthPeriod):
            deltaS = perPtfCloseDays[pDay] - perPtfCloseDays[0]
            weightedS = perPtfCloseDays[0]
            perPtfCloseAbsDays = np.append(perPtfCloseAbsDays, 100 * deltaS / weightedS)
    else:  # Случай присутствия пополнений-снятий в заданном нами диапазоне
        unqCashSumPeriod = np.zeros(unqCashQtyOperPeriod)
        for uCash in range(unqCashQtyOperPeriod):
            for pCash in range(cashQtyOper1):
                if unqCashDatesOperPeriod[uCash] == cashDatesOper1[pCash]:
                    if cashTypeOper1[pCash] == "Input":
                        unqCashSumPeriod[uCash] -= cashSum1[pCash]
                    else:
                        unqCashSumPeriod[uCash] += cashSum1[pCash]

        if iDateStart != iSDate:  # Случай несовпадения стартовой даты на диограмме с датой начала анализа портфеля
            unqCashSumPeriod = np.append([-perPtfCloseDays[0]], unqCashSumPeriod)
            unqCashDatesOperPeriod = np.append(perUnqDatesDays[0], unqCashDatesOperPeriod)
            unqCashQtyOperPeriod += 1

        timeVector = np.zeros((lengthPeriod, unqCashQtyOperPeriod))
        nakCashSum = np.zeros(unqCashQtyOperPeriod)  # Накопленная сумма пополнений и снятий (периоды)
        for uCash in range(unqCashQtyOperPeriod):
            nakCashSum[uCash] -= np.sum(unqCashSumPeriod[0:uCash + 1])

        # Вектор Input(-1) / Output(+1) индикаторов пополнений / снятий по дням
        vectorInOut = np.zeros((lengthPeriod, unqCashQtyOperPeriod))
        timeVectorTmp, vectorInOutTmp, s = np.zeros(unqCashQtyOperPeriod), np.zeros(unqCashQtyOperPeriod), 0
        for pDay in range(lengthPeriod):
            for uCash in range(unqCashQtyOperPeriod):
                if perUnqDatesDays[pDay] == unqCashDatesOperPeriod[uCash]:
                    vectorInOutTmp[uCash] += 1
                    s = uCash

            timeVectorTmp[s] += 1
            vectorInOut[pDay] = vectorInOutTmp
            timeVector[pDay] = timeVectorTmp

        # Цикл формирования массива доходностей портфеля по дням с учётом пополнениё-снятий (внутри периода)
        for pDay in range(lengthPeriod):
            deltaS = perPtfCloseDays[pDay] + np.dot(vectorInOut[pDay], unqCashSumPeriod)
            weightedS = np.dot(timeVector[pDay], nakCashSum) / (pDay + 1)
            perPtfCloseAbsDays = np.append(perPtfCloseAbsDays, 100 * deltaS / weightedS)

    return perUnqDatesDays, perPtfCloseAbsDays, weightedS


# Функция для рассчёта live-цен активов (массив открытых позиций)
# Входные кэшируемые параметры
# iABPrices - соответствует avgByuPrices (средняя цена покупки каждого актива по FIFO)
# iSPAs - соответствует startsPriceAs (начальная цена каждого актива)
# iQOpen - соответствует qualityOpen (количество открытых позиций каждого актива)
# iWASum - соответствует weightedAvgSum (взвешенная сумма с учётом пополнений-снятий)
# iOEmitents - соответствует unqEmitents (уникальные эмитенты открытых позиций)
# iOTickers - соответствует unqAsfInfOut (уникальные тикеры открытых позиций)
# iOExchanges - соответствует unqExfInfOut (уникальные биржы открытых позиций)
# iCashLast - соответствует freeCashVec[-1] -- Свободные деньги инвестора на последнюю дату анализа портфеля
# iCashLastRUB - соответствует freeCashVecRUB[-1] -- Свободные доллары инвестора на последнюю дату анализа портфеля
# iCashLastUSD - соответствует freeCashVecUSD[-1] -- Свободные рубли инвестора на последнюю дату анализа портфеля
# iPtfCloseLast - соответствует ptfCloseAbsDaysAll[-1] -- Цена закрытия портфея на последнюю дату анализа портфеля
# iForexPriceLast - соответствует forexCloseDays[-1] -- Цена закрытия курса валюты на последнюю дату анализа портфеля
# iForex - input forex (входная валюта анализа портфеля основной функции)
def dynamicPrices(iABPrices, iSPAs, iQOpen, iWASum, iOEmitents, iOTickers, iOExchanges,
                  iCashLast, iCashLastRUB, iCashLastUSD, iPtfCloseLast, iForexPriceLast, iForex):

    live_urls = []  # Курс доллара на данный момент времени
    live_urls.append(get_live_url('USDRUB', 'FOREX'))

    if not (' ' in iOTickers):
        unqOpenTickersCnt, liveArrPrice = len(iOTickers), []

        for i in range(unqOpenTickersCnt):
            live_urls.append(get_live_url(iOTickers[i], iOExchanges[i]))
        live_finance_data = asyncio.run(main(live_urls))

        # live-цены активов с учётом обрабоки NA
        for i in range(unqOpenTickersCnt):
            if live_finance_data[i + 1]['close'] == 'NA':
                liveArrPrice = np.append(liveArrPrice, live_finance_data[i + 1]['previousClose'])
            else:
                liveArrPrice = np.append(liveArrPrice, live_finance_data[i + 1]['close'])

        # live-цена курса валютной пары USDRUB с учётом обрабоки NA
        if live_finance_data[0]['close'] == 'NA':
            liveUSDPrice = live_finance_data[0]['previousClose']
        else:
            liveUSDPrice = live_finance_data[0]['close']

        # Конвертация live-цен активов согласно курсу валюты
        liveArrPriceTr, trSPAs = [], []  # Конвертированные live-цены / Не конвертированные live-цены
        for i in range(unqOpenTickersCnt):
            trLivePrice = forex_conversion(iForex, iOExchanges[i], liveArrPrice[i], liveUSDPrice)
            trAvg = forex_conversion(iForex, iOExchanges[i], iSPAs[i], liveUSDPrice)
            liveArrPriceTr = np.append(liveArrPriceTr, trLivePrice)
            trSPAs = np.append(trSPAs, trAvg)

        # Сумма инвестиций в актив
        startPrice = np.array(iQOpen) * np.array(iABPrices)

        # Текущая цена каждого актива с учетом количества
        thisPrice = np.array(iQOpen) * np.array(liveArrPrice)

        # Текущая конвертированная цена каждого актива в валюту анализа портфеля с учетом количества
        thisPriceTr = np.array(iQOpen) * np.array(liveArrPriceTr)

        # Текущая live - цена портфеля
        if iForex == 'USD':
            totCostPtf = iCashLastRUB / liveUSDPrice + iCashLastUSD + np.sum(np.array(thisPriceTr))
        else:
            totCostPtf = iCashLastRUB + iCashLastUSD * liveUSDPrice + np.sum(np.array(thisPriceTr))

        # Доля каждого актива от портфеля
        percentOfPtf = 100 * np.array(thisPriceTr) / totCostPtf

        # % изменения цены каждого актива
        percentChange = 100 * (np.array(liveArrPrice) / np.array(iABPrices) - 1)

        # Прибыль с открытых позиций портфеля
        openPositionsProfit = 100 * np.sum(np.array(thisPriceTr) - np.array(trSPAs)) / totCostPtf

    else:
        live_finance_data = asyncio.run(main(live_urls))
        liveUSDPrice = live_finance_data[0]['close']
        totCostPtf = iCashLast  # Текущая цена портфеля
        iOEmitents, iOTickers, iOExchanges, percentChange, openPositionsProfit = [], [], [], [], []
        liveArrPrice, iQOpen, startPrice, thisPrice, percentOfPtf, iABPrices = [], [], [], [], [], []

    percentOfPtfCash = 100 * iCashLast / totCostPtf  # Доля свободных денег инвестора в портфеле

    # Добавление информации о RUB / USD
    iOEmitents, iOTickers = np.append(iOEmitents, 'United States Dollar'), np.append(iOTickers, 'USD')
    iOEmitents, iOTickers = np.append(iOEmitents, 'Russian Ruble'), np.append(iOTickers, 'RUB')
    iABPrices, percentChange = np.append(iABPrices, '-'), np.append(percentChange, '-')
    iABPrices, percentChange = np.append(iABPrices, '-'), np.append(percentChange, '-')
    thisPriceAs, iQOpen = np.append(liveArrPrice, liveUSDPrice), np.append(iQOpen, iCashLastUSD)
    thisPriceAs, iQOpen = np.append(thisPriceAs, 1), np.append(iQOpen, iCashLastRUB)
    iOExchanges = np.append(iOExchanges, 'FOREX')
    iOExchanges = np.append(iOExchanges, 'FOREX')

    if iForex == 'USD':
        percentOfPtf = np.append(percentOfPtf, 100 * iCashLastUSD / totCostPtf)
        percentOfPtf = np.append(percentOfPtf, 100 * iCashLastRUB / (totCostPtf * iForexPriceLast))
    else:
        percentOfPtf = np.append(percentOfPtf, 100 * iCashLastUSD * iForexPriceLast / totCostPtf)
        percentOfPtf = np.append(percentOfPtf, 100 * iCashLastRUB / totCostPtf)

    startPrice, thisPrice = np.append(startPrice, '-'), np.append(thisPrice, '-')
    startPrice, thisPrice = np.append(startPrice, '-'), np.append(thisPrice, '-')

    oTemporary = np.array([totCostPtf, iCashLast, percentOfPtfCash, openPositionsProfit])

    oPositions = np.array([iOEmitents, iOTickers, iOExchanges, iABPrices, thisPriceAs, iQOpen,
                           percentOfPtf, startPrice, thisPrice, percentChange])

    return oTemporary, oPositions


# Функция, определяющая дату начала анализа портфеля
# iTransactions - операции покупок-продаж ценных бумаг
# iChanges - операции конвертации валюты
# iIncomeOutcome - операции пополнений-снятий денежных средств
def startDatePortfolio(iTransactions, iChanges, iInOut, iDividends):
    trTransactions, trChanges = transpose(iTransactions), transpose(iChanges)
    trInOut, trDividends = transpose(iInOut), transpose(iDividends)
    datesOper = []  # Массив дат старта типов операций
    if len(trTransactions) != 0:  # Даты операций с ценными бумагами (покупки-продаж)
        datesOperOne = min(trTransactions[0])
        datesOper.append(datesOperOne)
    if len(trChanges) != 0:  # Даты обмена валюты
        datesOperTwo = min(trChanges[0])
        datesOper.append(datesOperTwo)
    if len(trInOut) != 0:  # Даты пополнений-снятий денежных средств
        datesOperThree = min(trInOut[0])
        datesOper.append(datesOperThree)
    if len(trDividends) != 0:  # Даты начисления дивидендов
        datesOperFour = min(trDividends[0])
        datesOper.append(datesOperFour)

    sDates = min(datesOper)  # Стартовая дата анализа портфеля
    return sDates


# ------------------ Главная функция анализа портфеля (личный кабинет) ------------------
# Анализируем портфель на основе транзакций инвестора
# asset_transactions - массив покупок/продаж активов (акции, etf)
# cash_transactions - массив пополнения/снятия денежных средств (рубли РФ, доллары США)
# benchmark_ticker - тикер бенчмарка
# benchmark_exchange - биржа бенчмарка
# risk_free_ticker - тикер безрисковой ставки
# risk_free_exchange - безрисковой ставки
# base_currency - базовая валюта портфеля: USD или RUB)
# !! 2 ниже параметра идут на вход функции, для того, чтобы вывести на диаграмму доходность портфеля по дням
# start_chart_date - начальная дата графика доходности портфеля
# end_chart_date - конечная дата графика доходности портфеля
def analysingPortfolio(asset_transactions, cash_transactions, currency_transactions, dividend_transactions,
                       benchmark_ticker, benchmark_exchange, risk_free_ticker, risk_free_exchange,
                       base_currency, start_chart_date, end_chart_date):
    # Дата начала анализа портфеля
    date_format = '%Y-%m-%d'  # Формат даты начала анализа портфеля
    start_date = startDatePortfolio(asset_transactions, cash_transactions, currency_transactions, dividend_transactions)

    # Нужно понять какие тикеры у нас вообще есть
    # Разбиваем массив транзакций (покупок-продаж активов) на столбцы, обозначая их для дальнейшего анализа
    tickersQtyOper = len(asset_transactions)  # Количество операций инвестора с тикерами (строк массива)
    if tickersQtyOper == 0:
        asset_transactions = [[' ', ' ', ' ', ' ', ' ', 0, 1]]

    trArrayTickers = transpose(asset_transactions)  # Транспонирование матрицы транзакций с тикерами
    tickersDatesOper = np.array(trArrayTickers[0])  # Даты каждой операции

    # Формирование отсортированного массива транзакций инвестора
    sort_transactions = [asset_transactions[index] for index in np.argsort(tickersDatesOper)]
    trArrayTickers = transpose(sort_transactions)  # Транспонирование матрицы транзакций с тикерами
    tickersDatesOper = np.array(trArrayTickers[0])  # Даты каждой операции
    tickersOper = np.array(trArrayTickers[2])  # Тикеры каждой операции
    tickersExchange = np.array(trArrayTickers[3])  # Биржи тикеров
    tickersTypeOper = np.array(trArrayTickers[4])  # Тип каждой операции
    tickersPrice = np.array(trArrayTickers[5])  # Не конвертированная (!) цена покупки тикера (валюта зависит от биржи)
    tickersQty = np.array(trArrayTickers[6])  # Число купленных акций

    # Работа с тикерами
    unqTickerExchanges = np.unique([tickersOper, tickersExchange], axis=1)  # Уникальные пары тикер-биржа
    unqTickers = unqTickerExchanges[0]  # Уникальные тикеры
    unqExchanges = unqTickerExchanges[1]  # Биржи уникальных тикеров
    as_cnt = len(unqTickers)  # Количество уникальных тикеров
    eachTickersQty = np.zeros(as_cnt)  # Массив количества каждого из уникальных тикеров

    # Разбиваем массив пополнений/снятий валюты
    arrayCash = cash_transactions
    cashQtyOper = len(arrayCash)  # Количество операций инвестора с кэшэм (строк массива)
    if cashQtyOper == 0:
        arrayCash = [[' ', ' ', ' ', ' ', 0]]

    trArrayCash = transpose(arrayCash)  # Транспонирование матрицы транзакций с кэшэм
    cash_dates = np.array(trArrayCash[0])  # Даты каждой транзакции (пополнений или снятий)
    cash_type = np.array(trArrayCash[3])  # Тип транзакции (пополнить, снять)

    # Формирование отсортированного массива
    ind_cash = np.lexsort((cash_type, cash_dates))
    sort_cash = [arrayCash[index] for index in ind_cash]

    trArrayCash = transpose(sort_cash)  # Транспонирование матрицы транзакций с кэшэм
    cash_dates = np.array(trArrayCash[0])  # Даты каждой транзакции (пополнений или снятий)
    cashForex = np.array(trArrayCash[2])  # Валюта каждой транзакции (пополнений или снятий)
    cash_type = np.array(trArrayCash[3])  # Тип транзакции (пополнить, снять)
    cash_sum = np.array(trArrayCash[4], dtype='float64')  # Сумма транзакции (на счету у нас доллары и рубли)

    # Разбиваем массив обмена кэша на столбцы (покупка-продажа USD)
    changeQtyOper = len(currency_transactions)  # Количество операций обменя инвестора с кэшэм (строк массива)
    if changeQtyOper == 0:
        currency_transactions = [[' ', ' ', ' ', 0, 0]]

    trArrayChange = transpose(currency_transactions)  # Транспонирование матрицы транзакций с обменом валюты
    changeDatesOper = np.array(trArrayChange[0])  # Даты каждой транзакции (обмена валюты)
    changeTypeOper = np.array(trArrayChange[2])  # Тип транзакции (купить доллары, продать доллары)
    changePrice = np.array(trArrayChange[3])  # Цена покупки/продажи долларов
    changeQty = np.array(trArrayChange[4])  # Количество долларов для покупки/продажи

    # Разбиваем массив начисления дивидендов на столбцы
    dividendQtyOper = len(dividend_transactions)  # Количество операций начисленных дивидендов (строк массива)
    if dividendQtyOper == 0:
        dividend_transactions = [[' ', ' ', ' ', ' ', ' ', 0]]

    trArrayDividends = transpose(dividend_transactions)  # Транспонирование матрицы транзакций дивидендов
    dividendDatesOper = np.array(trArrayDividends[0])  # Даты каждого начисления дивидендов
    dividendExchange = np.array(trArrayDividends[3])  # Биржи тикеров каждого актива, которому начислили дивиденд
    dividendSum = np.array(trArrayDividends[5])  # Не конвертированная сумма дивиденда (валюта зависит от биржи)

    # Проверка операций на будние дни (операция может только совершаться в рабочие дни)
    for trade in range(tickersQtyOper):
        date_temp = datetime.strptime(tickersDatesOper[trade], date_format)
        if date_temp.weekday() in [5, 6]:
            return "Установите рабочий день для совершения операции"

    for cash in range(cashQtyOper):
        date_temp = datetime.strptime(cash_dates[cash], date_format)
        if date_temp.weekday() in [5, 6]:
            return "Установите рабочий день для совершения операции"

    for change in range(changeQtyOper):
        date_temp = datetime.strptime(changeDatesOper[change], date_format)
        if date_temp.weekday() in [5, 6]:
            return "Установите рабочий день для совершения операции"

    for div in range(dividendQtyOper):
        date_temp = datetime.strptime(dividendDatesOper[div], date_format)
        if date_temp.weekday() in [5, 6]:
            return "Установите рабочий день для совершения операции"

    # Определяем дату конца анализа портфеля
    # Если дата конца анализа портфеля суббота или воскресенье, то мы берём последнюю пятницу
    end_date = datetime.today()
    date_today = end_date  # Сегодняшняя дата (нужна для расчётов)
    while end_date.weekday() in [5, 6]:
        end_date = end_date - timedelta(days=+ 1)

    end_date = datetime.strftime(end_date, date_format)
    ptf_daily_dates = days_in_range(start_date, end_date)  # Формируем массив дат
    end_date = ptf_daily_dates[-1]  # Конечная дата анализа портфеля

    # Для избежания построения неккоретного графиков доходностей портфеля, бенчмарка, безрисковой ставки
    # Для этого вычитаем со стартовой даты анализа портфеля 5 дней (вполне достаточно) для запроса к eod_historical_data
    # Бывают случаи, что портфель начинается со вторника, а ближайшие цены закрытия бенчмарка были
    # в понедельник и среду, соответственно необходимо цену вторника заполнять ценой понедельника
    start_date_url = datetime.strptime(start_date, date_format)
    start_date_url -= relativedelta(days=5)
    start_date_url = datetime.strftime(start_date_url, date_format)

    # Формирование url-запросов цен закрытия активов к eod
    url_requests, len_tickers = [], 0
    if ' ' not in unqTickers:
        len_tickers = as_cnt
        for i in range(as_cnt):
            url_requests.append(get_url(unqTickers[i], unqExchanges[i], start_date_url, end_date))

    # Формирование url-запросов цен закрытия бенчмарка и безрисковой ставки к eod
    url_requests.append(get_url(benchmark_ticker, benchmark_exchange, start_date_url, end_date))
    url_requests.append(get_url(risk_free_ticker, risk_free_exchange, start_date_url, end_date))

    # Формирование url-запросов сплитов активов к eod
    if ' ' not in unqTickers:
        for i in range(as_cnt):
            url_temp = get_url(unqTickers[i], unqExchanges[i], start_date, end_date)
            url_temp = url_temp.replace('/eod/', '/splits/')
            url_requests.append(url_temp)
    url_requests.append(get_url("USDRUB", "FOREX", start_date_url, end_date))

    # Формирование массива финансовых данных
    # Цены закрытия активов, цены закрытия и безрисковой ставки, сплиты активов, цены котировки валюты USDRUB
    finance_data = asyncio.run(main(url_requests))

    # Формирование дневных цен закрытия активов, бенчмарка и безрисковой ставки
    # !!! as_daily_prices - это для расчёта стоимости портфеля на каждый день
    as_start_dates = []  # Даты старта каждого из активов в портфеле
    ptf_days_cnt = len(ptf_daily_dates)  # Количество дневных дат существования портфеля
    as_daily_prices, forex_daily_prices_ptf = [[]] * as_cnt, []  # Дневные цены закрытия активов / курса валюты USDRUB
    bench_daily_dates, bench_daily_prices = [], []  # Дневные даты бенчмарка / цены закрытия бенчмарка
    rf_daily_dates, rf_daily_prices = [], []  # Дневные даты безрисковой ставки / цены закрытия безрисковой ставки
    for i in range(len_tickers + 2):
        dates, prices = [], []
        for j in range(len(finance_data[i])):
            dates = np.append(dates, finance_data[i][j]['date'])
            prices = np.append(prices, finance_data[i][j]['close'])

        if i < len_tickers:
            # Обработка ошибки транзакции в дату, когда актив не торговался в ЛК
            for j in range(len(sort_transactions)):
                if (tickersDatesOper[j] < dates[0]) and (unqTickers[i] == tickersOper[j]):
                    min_date = datetime.strptime(dates[0], date_format)
                    min_date = datetime.strftime(min_date, '%d.%m.%Y')
                    return "Невозможно добавить транзакцию с датой ранее " + min_date

            as_daily_prices[i] = alignment_prices(ptf_daily_dates, dates, prices)
            if start_date <= dates[0]:
                as_start_dates = np.append(as_start_dates, dates[0])
            else:
                as_start_dates = np.append(as_start_dates, start_date)

        elif i == len_tickers:
            if start_date <= dates[0]:
                bench_daily_dates = days_in_range(dates[0], end_date)
            else:
                bench_daily_dates = days_in_range(start_date, end_date)
            bench_daily_prices = alignment_prices(bench_daily_dates, dates, prices)

        else:
            if start_date <= dates[0]:
                rf_daily_dates = days_in_range(dates[0], end_date)
            else:
                rf_daily_dates = days_in_range(start_date, end_date)
            rf_daily_prices = alignment_prices(rf_daily_dates, dates, prices)
    as_daily_prices = np.array(as_daily_prices)

    if ' ' in unqTickers:
        as_daily_prices = np.zeros((1, ptf_days_cnt))

    # Формирование дневных цен курса валюты
    forex_prices, forex_dates = [], []
    for j in range(len(finance_data[2 * len_tickers + 2])):
        forex_dates = np.append(forex_dates, finance_data[2 * len_tickers + 2][j]['date'])
        forex_prices = np.append(forex_prices, finance_data[2 * len_tickers + 2][j]['close'])
    forex_daily_prices_ptf = alignment_prices(ptf_daily_dates, forex_dates, forex_prices)
    forex_daily_prices_bench = alignment_prices(bench_daily_dates, forex_dates, forex_prices)
    forex_daily_prices_rf = alignment_prices(rf_daily_dates, forex_dates, forex_prices)

    # Цикл применения конвертации цен закрытия активов портфеля в валюту анализа портфеля
    for i in range(len_tickers):
        as_daily_prices[i] = forex_conversion(base_currency, unqExchanges[i], as_daily_prices[i], forex_daily_prices_ptf)

    # Конвертация бенчмарка в валюту анализа портфеля
    if (benchmark_ticker in ['SP500TR', 'GSPC', 'IXIC', 'NDX', 'ACWI', 'MSCIWORLD']) and (base_currency == 'RUB'):
        bench_daily_prices *= forex_daily_prices_bench
    if (benchmark_ticker in ['IMOEX', 'MCFTR']) and (base_currency == 'USD'):
        bench_daily_prices /= forex_daily_prices_bench

    # Конвертация безрисковой ставки в валюту анализа портфеля
    if (risk_free_ticker == 'IDCOT10TR') and (base_currency == 'RUB'):
        rf_daily_prices *= forex_daily_prices_rf
    if (risk_free_ticker == 'RGBITR') and (base_currency == 'USD'):
        rf_daily_prices /= forex_daily_prices_rf

    # Определение сприлов активов
    splits = []
    if ' ' not in unqTickers:
        splits_data = finance_data[as_cnt + 2: 2 * as_cnt + 2]
        for i in range(len(splits_data)):
            splits.append(get_split_data(splits_data[i]))
    else:
        splits = [[['1900-01-01'], [1]]]

    # Функция рассчёта цен закрытия портфеля по дням
    # Цикл рассчёта свободных денег инвестора по дням (рублей и долларов), и общей суммы в валюте анализа портфеля
    # С учётом покупки-продажи активов, пополнений-снятий денежных средств, конвертации валют
    tmpVecUSD, tmpVecRUB = 0, 0
    freeCashVecUSD, freeCashVecRUB = np.zeros(ptf_days_cnt), np.zeros(ptf_days_cnt)

    eachTickerQtyDays = [[0] * as_cnt]
    for day in range(ptf_days_cnt):
        for cash in range(cashQtyOper):
            if ptf_daily_dates[day] == cash_dates[cash]:
                if cash_type[cash] == 'Input' and cashForex[cash] == 'USD':
                    tmpVecUSD += cash_sum[cash]
                elif cash_type[cash] == 'Input' and cashForex[cash] == 'RUB':
                    tmpVecRUB += cash_sum[cash]
                elif cash_type[cash] == 'Output' and cashForex[cash] == 'USD':
                    tmpVecUSD -= cash_sum[cash]
                else:
                    tmpVecRUB -= cash_sum[cash]

        for div in range(dividendQtyOper):
            if ptf_daily_dates[day] == dividendDatesOper[div]:
                if dividendExchange[div] == 'MCX':
                    tmpVecRUB += dividendSum[div]
                else:
                    tmpVecUSD += dividendSum[div]

        for change in range(changeQtyOper):
            if ptf_daily_dates[day] == changeDatesOper[change]:
                if changeTypeOper[change] == 'Buy':
                    tmpVecUSD += changeQty[change]
                    tmpVecRUB -= changeQty[change] * changePrice[change]
                else:
                    tmpVecUSD -= changeQty[change]
                    tmpVecRUB += changeQty[change] * changePrice[change]

                if tmpVecUSD < 0 or tmpVecRUB < 0:
                    return "Недостаточно средств"

        for trade in range(tickersQtyOper):
            if ptf_daily_dates[day] == tickersDatesOper[trade]:
                index, = np.where(unqTickers == tickersOper[trade])[0]
                if tickersTypeOper[trade] == 'Buy' and tickersExchange[trade] == 'MCX':
                    eachTickersQty[index] += tickersQty[trade]
                    tmpVecRUB -= tickersPrice[trade] * tickersQty[trade]
                elif tickersTypeOper[trade] == 'Buy' and tickersExchange[trade] != 'MCX':
                    eachTickersQty[index] += tickersQty[trade]
                    tmpVecUSD -= tickersPrice[trade] * tickersQty[trade]
                elif tickersTypeOper[trade] == 'Sell' and tickersExchange[trade] == 'MCX':
                    eachTickersQty[index] -= tickersQty[trade]
                    tmpVecRUB += tickersPrice[trade] * tickersQty[trade]
                else:
                    eachTickersQty[index] -= tickersQty[trade]
                    tmpVecUSD += tickersPrice[trade] * tickersQty[trade]

                if eachTickersQty[index] < 0:
                    return "Учёт «коротких» позиций (маржинальных сделок) невозможен. " \
                           "Установите меньшее количество актива"

        if tmpVecUSD < 0 or tmpVecRUB < 0:
            return "Недостаточно средств"

        for split in range(as_cnt):
            for spl in range(len(splits[split][0])):
                if ptf_daily_dates[day] == splits[split][0][spl]:
                    eachTickersQty[split] *= splits[split][1][spl]

        eachTickerQtyDays = np.append(eachTickerQtyDays, [eachTickersQty], axis=0)
        freeCashVecUSD[day] = tmpVecUSD
        freeCashVecRUB[day] = tmpVecRUB

    # Рассчёт стоимости чистых активов (открытых позиций) по дням
    netAssetValueDays, eachTickerQtyDays = np.zeros(ptf_days_cnt), np.delete(eachTickerQtyDays, 0, axis=0)
    for day in range(ptf_days_cnt):
        netAssetValueDays[day] = np.dot(eachTickerQtyDays[day], as_daily_prices.transpose()[day])

    # Вектор свободных денег инвестора по дням
    if base_currency == 'USD':
        freeCashVec = freeCashVecUSD + freeCashVecRUB / forex_daily_prices_ptf
    else:
        freeCashVec = freeCashVecUSD * forex_daily_prices_ptf + freeCashVecRUB

    # Цены закрытия инвестиционного портфеля по дням
    ptf_daily_prices = freeCashVec + netAssetValueDays

    # Перевод валюты пополнений-снятий в валюту анализа портфеля (с учётом курса на день пополнения-снятия)
    for cash in range(cashQtyOper):
        j, = np.where(ptf_daily_dates == cash_dates[cash])[0]
        if base_currency == "USD" and cashForex[cash] == "RUB":
            cash_sum[cash] /= forex_daily_prices_ptf[j]
        elif base_currency == "RUB" and cashForex[cash] == "USD":
            cash_sum[cash] *= forex_daily_prices_ptf[j]

    # Доходность портфеля на всём периоде по дням с учётом пополнений и снятий
    portfolioAll = returnsPortfolioPeriod(cash_transactions, base_currency,
                                          ptf_daily_dates, ptf_daily_prices,
                                          forex_daily_prices_ptf, start_date,
                                          'None', 'None')

    # Доходность портфеля на периоде внутри анализа портфеля по дням с учётом пополнений и снятий
    ptfCloseAbsDaysCurve = returnsPortfolioPeriod(cash_transactions, base_currency,
                                                  ptf_daily_dates, ptf_daily_prices,
                                                  forex_daily_prices_ptf, start_date,
                                                  start_chart_date, end_chart_date)

    # Для построения корректного графика
    newDays = returnsPortfolioPeriod(cash_transactions, base_currency,
                                     ptf_daily_dates, ptf_daily_prices,
                                     forex_daily_prices_ptf, start_date,
                                     start_chart_date, end_chart_date)

    # График доходности портфеля / взвешенная сумма стоимости портфеля
    ptf_abs_profits_chart, weightedAvgSum = portfolioAll[1], portfolioAll[2]

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # Работа с датами для рассчёта доходностей и статистических параметров портфеля
    # Период рассматриваемого портфеля мы огругляем с точностью до месяцев, чтобы рассчитывать GAGR
    ptf_start_date = datetime.strptime(start_date, date_format)  # Начальная дата анализа портфеля (формат datetime)
    ptf_end_date = datetime.strptime(end_date, date_format)  # Конечная дата анализа портфеля (формат datetime)
    ptf_diff_dates = relativedelta(ptf_end_date, ptf_start_date)  # Разность даты конца и даты начала
    ptf_months_cnt = ptf_diff_dates.years * 12 + ptf_diff_dates.months  # Количество полных месяцев анализируемого периода портфеля

    # Для расчёта доходностей портфеля за определённый период в месяцах
    # 1, 3, 6, 12 = 1 год, YTD - с начала года, All - за весь период
    def ptf_return(return_period):
        k = -1
        if return_period == 'All':
            return ptf_abs_profits_chart[-1]
        elif return_period == 'YTD':
            ptf_return_date = datetime(ptf_end_date.year, 1, 1)
        elif return_period == 'Yesterday':
            if datetime.today().weekday() not in [5, 6]: k -= 1
            ptf_return_date = datetime.strptime(ptf_daily_dates[k - 1], date_format)
        else:
            ptf_return_date = ptf_end_date - relativedelta(months=+ return_period)
        ptf_return_date = datetime.strftime(ptf_return_date, date_format)
        ptf_return_date = search_date(ptf_daily_dates, ptf_return_date, '-')
        ptf_profit = returnsPortfolioPeriod(cash_transactions, base_currency,
                                            ptf_daily_dates, ptf_daily_prices,
                                            forex_daily_prices_ptf, start_date,
                                            ptf_return_date, end_date)[1][k]

        return ptf_profit

    # Расчёт показателей абсолютной доходности портфеля (в зависимости от периода существования портфеля)
    ptf_abs_profit_all = ptf_return("All")
    if ptf_months_cnt < 1:
        ptf_abs_profits = [ptf_abs_profit_all]
    elif 1 <= ptf_months_cnt < 3:
        ptf_abs_profits = [ptf_return(1), ptf_abs_profit_all]
    elif 3 <= ptf_months_cnt < 6:
        ptf_abs_profits = [ptf_return(1), ptf_return(3), ptf_abs_profit_all]
    elif 6 <= ptf_months_cnt < 12:
        ptf_abs_profits = [ptf_return(1), ptf_return(3), ptf_return(6), ptf_abs_profit_all]
    else:
        ptf_abs_profits = [ptf_return(1), ptf_return(3), ptf_return(6), ptf_return(12), ptf_abs_profit_all]

    # Расчёт доходности YTD портфеля (в зависимости от старта года)
    if ptf_end_date.year - ptf_start_date.year > 0:
        ptf_abs_profits = np.insert(ptf_abs_profits, -1, ptf_return("YTD"))
    else:
        ptf_abs_profits = np.insert(ptf_abs_profits, -1, ptf_abs_profit_all)

    # Изменение за вчера (портфель)
    if len(ptf_daily_dates) > 2:
        ptf_abs_profit_yesterday = ptf_return('Yesterday')
        ptf_abs_profits = np.append(ptf_abs_profits, ptf_abs_profit_yesterday)
    elif len(ptf_daily_dates) == 2 and date_today.weekday() in [5, 6]:
        ptf_abs_profit_yesterday = ptf_return('Yesterday')
        ptf_abs_profits = np.append(ptf_abs_profits, ptf_abs_profit_yesterday)

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # Для расчёта доходностей бенчмарка/безрисковой (индексы) за определённый период в месяцах
    # 1, 3, 6, 12 = 1 год, YTD - с начала года, All - за весь период
    def ind_return(return_period, ind_end_date, ind_dates, ind_prices):
        k = - 2
        if datetime.today().weekday() in [5, 6]: k += 1
        if return_period == 'All':
            return 100 * (ind_prices[-1] / ind_prices[0] - 1)
        elif return_period == 'YTD':
            ind_return_date = datetime(ind_end_date.year, 1, 1)
        elif return_period == 'Yesterday':
            return 100 * (ind_prices[k] / ind_prices[k - 1] - 1)
        else:
            ind_return_date = ind_end_date - relativedelta(months=+ return_period)
        ind_return_date = datetime.strftime(ind_return_date, date_format)
        ind_return_date = search_date(ind_dates, ind_return_date, '-')
        k, = np.where(ind_dates == ind_return_date)[0]
        ind_profit = 100 * (ind_prices[-1] / ind_prices[k] - 1)

        return ind_profit

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # Работа с датами для рассчёта доходностей и статистических параметров бенчмарка
    # Период рассматриваемого бенчмарка мы огругляем с точностью до месяцев, чтобы рассчитывать GAGR
    bench_start_date = datetime.strptime(bench_daily_dates[0], date_format)  # Дата старта бенчмарка (формат datetime)
    bench_end_date = datetime.strptime(bench_daily_dates[-1], date_format)  # Дата конца бенчмарка (формат datetime)
    bench_diff_dates = relativedelta(bench_end_date, bench_start_date)  # Разность даты конца и даты начала
    bench_months_cnt = bench_diff_dates.years * 12 + bench_diff_dates.months  # Количество полных месяцев периода существования бенчмарка

    # Расчёт показателей абсолютной доходности бенчмарка
    # !В зависимости от периода существования бенчмарка
    bench_abs_profit_all = ind_return("All", bench_end_date, bench_daily_dates, bench_daily_prices)
    bench_abs_profits = [bench_abs_profit_all]
    if bench_months_cnt >= 1:
        bench_abs_profit_1months = ind_return(1, bench_end_date, bench_daily_dates, bench_daily_prices)
        bench_abs_profits = np.insert(bench_abs_profits, -1, bench_abs_profit_1months)
    if bench_months_cnt >= 3:
        bench_abs_profit_3months = ind_return(3, bench_end_date, bench_daily_dates, bench_daily_prices)
        bench_abs_profits = np.insert(bench_abs_profits, -1, bench_abs_profit_3months)
    if bench_months_cnt >= 6:
        bench_abs_profit_6months = ind_return(6, bench_end_date, bench_daily_dates, bench_daily_prices)
        bench_abs_profits = np.insert(bench_abs_profits, -1, bench_abs_profit_6months)
    if bench_months_cnt >= 12:
        bench_abs_profit_1year = ind_return(12, bench_end_date, bench_daily_dates, bench_daily_prices)
        bench_abs_profits = np.insert(bench_abs_profits, -1, bench_abs_profit_1year)

    # Рассчёт доходности YTD бенчмарка (в зависимости от старта года)
    if bench_end_date.year - bench_start_date.year > 0:
        bench_abs_profit_ytd = ind_return('YTD', bench_end_date, bench_daily_dates, bench_daily_prices)
    else:
        bench_abs_profit_ytd = bench_abs_profit_all
    bench_abs_profits = np.insert(bench_abs_profits, -1, bench_abs_profit_ytd)

    # Изменение за вчера (бенчмарк)
    if len(bench_daily_dates) > 2:
        bench_abs_profit_yesterday = ind_return('Yesterday', bench_end_date, bench_daily_dates, bench_daily_prices)
        bench_abs_profits = np.append(bench_abs_profits, bench_abs_profit_yesterday)
    elif len(bench_daily_dates) == 2 and date_today.weekday() in [5, 6]:
        bench_abs_profit_yesterday = ind_return('Yesterday', bench_end_date, bench_daily_dates, bench_daily_prices)
        bench_abs_profits = np.append(bench_abs_profits, bench_abs_profit_yesterday)

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # Работа с датами для рассчёта доходностей и статистических параметров безрисковой ставки
    # Период рассматриваемой безрисковой ставки мы огругляем с точностью до месяцев, чтобы рассчитывать GAGR
    rf_start_date = datetime.strptime(rf_daily_dates[0], date_format)  # Дата старта бенчмарка (формат datetime)
    rf_end_date = datetime.strptime(rf_daily_dates[-1], date_format)  # Дата конца бенчмарка (формат datetime)
    rf_diff_dates = relativedelta(rf_end_date, rf_start_date)  # Разность даты конца и даты начала
    rf_months_cnt = rf_diff_dates.years * 12 + rf_diff_dates.months  # Количество полных месяцев периода существования бенчмарка

    # Расчёт показателей абсолютной доходности безрисковой ставки
    # !В зависимости от периода существования безрисковой ставки
    rf_abs_profit_all = ind_return("All", rf_end_date, rf_daily_dates, rf_daily_prices)
    rf_abs_profits = [rf_abs_profit_all]
    if rf_months_cnt >= 1:
        rf_abs_profit_1months = ind_return(1, rf_end_date, rf_daily_dates, rf_daily_prices)
        rf_abs_profits = np.insert(rf_abs_profits, -1, rf_abs_profit_1months)
    if rf_months_cnt >= 3:
        rf_abs_profit_3months = ind_return(3, rf_end_date, rf_daily_dates, rf_daily_prices)
        rf_abs_profits = np.insert(rf_abs_profits, -1, rf_abs_profit_3months)
    if rf_months_cnt >= 6:
        rf_abs_profit_6months = ind_return(6, rf_end_date, rf_daily_dates, rf_daily_prices)
        rf_abs_profits = np.insert(rf_abs_profits, -1, rf_abs_profit_6months)
    if rf_months_cnt >= 12:
        rf_abs_profit_1year = ind_return(12, rf_end_date, rf_daily_dates, rf_daily_prices)
        rf_abs_profits = np.insert(rf_abs_profits, -1, rf_abs_profit_1year)

    # Рассчёт доходности YTD безрисковой ставки (в зависимости от старта года)
    if rf_end_date.year - rf_start_date.year > 0:
        rf_abs_profit_ytd = ind_return('YTD', rf_end_date, rf_daily_dates, rf_daily_prices)
    else:
        rf_abs_profit_ytd = rf_abs_profit_all
    rf_abs_profits = np.insert(rf_abs_profits, -1, rf_abs_profit_ytd)

    # Изменение за вчера (безрисковая ставка)
    if len(rf_daily_dates) > 2:
        rf_abs_profit_yesterday = ind_return('Yesterday', rf_end_date, rf_daily_dates, rf_daily_prices)
        rf_abs_profits = np.append(rf_abs_profits, rf_abs_profit_yesterday)
    elif len(rf_daily_dates) == 2 and date_today.weekday() in [5, 6]:
        rf_abs_profit_yesterday = ind_return('Yesterday', rf_end_date, rf_daily_dates, rf_daily_prices)
        rf_abs_profits = np.append(rf_abs_profits, rf_abs_profit_yesterday)

    # Для вывода абсолютных показателей доходности портфеля, бенчмарка, безрисковой ставки
    abs_profits_by_periods = np.array([ptf_abs_profits, bench_abs_profits, rf_abs_profits])

    # Рассчёт открытых/закрытых позиций портфеля инвестора методом First In -> First Out
    indSortTradeJournal = np.lexsort((tickersDatesOper, tickersOper))  # Отсортированный массив tradeJournal
    sortTradeJournal = [sort_transactions[index] for index in indSortTradeJournal]  # Формирование отсортированного массива
    trSortTradeJournal = transpose(sortTradeJournal)  # Транспонирование отсортированного массива
    sortTradeDates = trSortTradeJournal[0]  # Даты отсортированного массива операций
    sortAs = trSortTradeJournal[2]  # Тикеры отсортированного массива операций

    used = set()  # Массив уникальных тикеров (отсортированный)
    unqAsSort = np.array([ticker for ticker in sortAs if ticker not in used and (used.add(ticker) or True)])

    unqTickersQtySort = len(unqAsSort)  # Количество уникальных тикеров
    for tInd in range(tickersQtyOper):
        for sSplit in range(as_cnt):
            if unqAsSort[sSplit] == sortAs[tInd]:
                for spl in range(len(splits[sSplit][0])):
                    if sortTradeDates[tInd] < splits[sSplit][0][spl]:
                        trSortTradeJournal[6][tInd] = float(trSortTradeJournal[6][tInd]) * float(splits[sSplit][1][spl])
                        trSortTradeJournal[5][tInd] = float(trSortTradeJournal[5][tInd]) / float(splits[sSplit][1][spl])

    # Цикл для обработки массива методом FIFO
    buyPrices, sellPrices = [], []  # Создаём 2 пустых массива для цены покупок активов и цены продаж активов
    fInfOutCnt = [0] * unqTickersQtySort  # Количество купленных бумаг каждого актива
    for tInd in range(unqTickersQtySort):
        for trade in range(tickersQtyOper):
            if unqAsSort[tInd] == tickersOper[trade]:
                fInfOutCnt[tInd] += 1

    # Цикл для последующего рассчёта открытых и закрытых позиций в портфеле
    # Характеризует метод First In -> First Out + также доходность каждого актива при продаже
    fInfOut = transpose(trSortTradeJournal)
    for tInd in range(unqTickersQtySort):  # tNnd - индекс, под которым стоит тот или иной тикер
        sellPrice, sellCnt, totalSellPrice = 0, 0, 0
        buyPrice, buyCnt, totalBuyPrice = 0, 0, 0

        for trade in range(tickersQtyOper):
            if fInfOut[trade][4] == 'Buy' and unqAsSort[tInd] == fInfOut[trade][2]:
                buyCnt = fInfOut[trade][6]
                buyPrice = fInfOut[trade][5]
                totalBuyPrice += buyCnt * buyPrice
        buyPrices.append(totalBuyPrice)

        for trade in range(tickersQtyOper):
            if fInfOut[trade][4] == 'Sell' and unqAsSort[tInd] == fInfOut[trade][2]:
                sellCnt = fInfOut[trade][6]
                sellPrice = fInfOut[trade][5]
                totalSellPrice += sellCnt * sellPrice

                for subtrade in range(trade):
                    while fInfOut[subtrade][4] == 'Buy' and fInfOut[subtrade][2] == unqAsSort[tInd] \
                            and fInfOut[subtrade][6] > 0 and sellCnt > 0:
                        fInfOut[subtrade][6] -= 1
                        sellCnt -= 1
        sellPrices.append(totalSellPrice)

    # Открытые позиции, рассчитанные по методу First In -> First Out
    for i in range(len(fInfOut) - 1, -1, -1):
        if (fInfOut[i][4] == 'Buy' and fInfOut[i][6] == 0) or fInfOut[i][4] == 'Sell':
            del fInfOut[i]

    if len(fInfOut) == 0:
        fInfOut = [[' ', ' ', ' ', ' ', ' ', 0, 1]]

    # Обработка массива открытых позиций
    trfInfOut, length = transpose(fInfOut), len(fInfOut)  # Транспонирование матрицы, длина массива открытых позиций
    emitents, asFInFOut, exFInFOut, = trfInfOut[1], trfInfOut[2], trfInfOut[3]  # Эмитент, тикер, биржа актива
    pricesOpen, qtyOpen = trfInfOut[5], trfInfOut[6]  # Цена открытия позиции, число купленных активов

    used = set()  # Массив уникальных эмитентов открытых позиций
    unqFInFOut = np.unique([asFInFOut, exFInFOut, emitents], axis=1)  # Уникальные тройки тикер-биржа-эмитенты
    # Уникальные тикеры, биржи уникальных тикеров, эмитенты
    as_after_fifo, unqExfInfOut, unqEmitents = unqFInFOut[0], unqFInFOut[1], unqFInFOut[2]

    open_pos_start_dates = []
    if ' ' not in as_after_fifo:
        for ticker in as_after_fifo:
            j, = np.where(unqAsSort == ticker)[0]
            open_pos_start_dates.append(as_start_dates[j])

    # Цены открытых позиций (с чётом всех тикеров)
    startAsPricesAll = []
    for num in range(as_cnt):
        avgBuy, qtyOpenS = 0, 0
        for t in range(length):
            if asFInFOut[t] == unqAsSort[num]:
                avgBuy += pricesOpen[t] * qtyOpen[t]
        startAsPricesAll.append(avgBuy)

    # Цены открытых позиций без учёта всех тикеров
    avgByuPrices, qualityOpen, startsPriceAs = [], [], []
    open_as_cnt = len(as_after_fifo)
    for num in range(open_as_cnt):
        avgBuy, qtyOpenS = 0, 0
        for t in range(length):
            if asFInFOut[t] == as_after_fifo[num]:
                avgBuy += pricesOpen[t] * qtyOpen[t]
                qtyOpenS += qtyOpen[t]

        startsPriceAs.append(avgBuy)
        avgBuy /= qtyOpenS
        avgByuPrices.append(avgBuy)
        qualityOpen.append(qtyOpenS)

    dynamic = dynamicPrices(avgByuPrices, startsPriceAs, qualityOpen, weightedAvgSum,
                            unqEmitents, as_after_fifo, unqExfInfOut,
                            freeCashVec[-1], freeCashVecRUB[-1], freeCashVecUSD[-1],
                            ptf_abs_profits_chart[-1], forex_daily_prices_ptf[-1], base_currency)

    # Для вывода (прочие показатели портфеля, массив открытых позиций портфеля)
    othersTemporary, openPositions = dynamic[0], dynamic[1]

    # Недельные даты в рамках анализа портфеля
    ptf_weekly_dates = weeks_in_range(start_date, end_date)
    ptf_weeks_cnt = len(ptf_weekly_dates)

    # Для корректной отрисовки графика пересчёта доходностей
    i = 0
    for myday in ptf_daily_prices:
        newDays[1][i] = ptf_daily_prices[i]
        i = i + 1

    # Если портфелю менее 30 недель, то параметры портфеля не подлежат расчёту (не возвращаем их)
    if ptf_weeks_cnt < 30:
        return bench_daily_dates, bench_daily_prices, rf_daily_dates, rf_daily_prices, \
               ptf_daily_dates, ptfCloseAbsDaysCurve, forex_daily_prices_ptf, start_date, freeCashVecRUB[-1], \
               freeCashVecUSD[-1], abs_profits_by_periods, openPositions, othersTemporary, \
               startsPriceAs, weightedAvgSum, unqExfInfOut, newDays

    # Для рассчёта статистических параметров цен закрытия активов
    # Вычисляем цены закрытия активов с учётом сплитов (при доступном периоде)
    for day in range(ptf_days_cnt):
        for split in range(as_cnt):
            for spl in range(len(splits[split][0])):
                if ptf_daily_dates[day] >= splits[split][0][spl]:
                    as_daily_prices[split][day] *= splits[split][1][spl]

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # Логика расчётов портфельных показателей на общем периоде портфеля/бенчмарка/безрисковой ставки

    # Операции с датами
    # /////////////////////////////////////////////

    # ---
    # Начальная максимальная дата портфеля/бенчмарка/безрисковой ставки как дата старта самого молодого актива
    gagr_start_date = max(ptf_daily_dates[0], bench_daily_dates[0], rf_daily_dates[0])
    gagr_start_date = datetime.strptime(gagr_start_date, date_format)  # Перевод начальной максимальной
    gagr_end_date = datetime.strptime(end_date, date_format)  # и конечной дат общего периода в формат datetime

    # Необходимая дата для расчёта GAGR портфеля,бенчмарка/безрисковой ставки
    gagr_diff_dates = relativedelta(gagr_end_date, gagr_start_date)  # Находим разность между двумя датами
    gagr_months_cnt = gagr_diff_dates.years * 12 + gagr_diff_dates.months  # Число месяцев между двумя датами
    gagr_date = gagr_start_date + relativedelta(months=+ gagr_months_cnt)  # Конечная дата для расчёта GAGR
    gagr_date = datetime.strftime(gagr_date, date_format)  # Перевод конечной даты для расчёта GAGR в формат str

    # Перевод дат в формат str
    gagr_start_date = datetime.strftime(gagr_start_date, date_format)  # Перевод начальной максимальной
    gagr_end_date = datetime.strftime(gagr_end_date, date_format)  # и конечной даты общего периода в формат str

    # Формирование массива дневных и недельных дат общего периода портфеля/бенчмарка/безрисковой ставки
    gagr_daily_dates = days_in_range(gagr_start_date, gagr_end_date)  # Дневные даты
    gagr_weekly_dates = weeks_in_range(gagr_start_date, gagr_end_date)  # Недельные даты
    gagr_date = search_date(gagr_daily_dates, gagr_date, '-')  # Поиск нужной даты для расчёта GAGR (если выходной)
    gagr_weeks_cnt = len(gagr_weekly_dates)  # Количество недель общего периода

    # Подготовка данных портфеля с учётом общего gagr периода
    # /////////////////////////////////////////////

    # ---
    # Цикл формирования недельных цен закрытия портфеля
    ptf_weekly_prices = []
    for ptf_date in gagr_weekly_dates:
        j, = np.where(ptf_daily_dates == ptf_date)[0]
        ptf_weekly_prices = np.append(ptf_weekly_prices, ptf_daily_prices[j])

    # ---
    # Расчёт логарифмов отношения недельных цен закрытия портфеля с учётом пополнений и снятий (для расчёта статистик)
    # !!! Для расчёта волатильности портфеля
    ptf_weekly_ln = np.zeros(gagr_weeks_cnt)
    cash_flow = 0  # Расчёт первого логарифма отношения цен закрытия портфеля
    if gagr_daily_dates[0] == start_date:
        for cash in range(cashQtyOper):
            if cash_dates[cash] == start_date:
                if cash_type[cash] == "Input":
                    cash_flow += cash_sum[cash]
                else:
                    cash_flow -= cash_sum[cash]
        ptf_weekly_ln[0] = np.log(ptf_weekly_prices[0] / cash_flow)

    for w in range(gagr_weeks_cnt - 1):  # Расчёт остальных логарифмов отношений цен закрытия портфеля
        ptf_weekly_ln[w + 1] = np.log(ptf_weekly_prices[w + 1] / ptf_weekly_prices[w])
        if ptf_weekly_dates[w] != gagr_start_date:
            cash_flow = 0
            for cash in range(cashQtyOper):
                if ptf_weekly_dates[w] < cash_dates[cash] <= ptf_weekly_dates[w + 1]:
                    if cash_type[cash] == "Input":
                        cash_flow += cash_sum[cash]
                    else:
                        cash_flow -= cash_sum[cash]
                    ptf_weekly_ln[w + 1] = np.log((ptf_weekly_prices[w + 1] - cash_flow) / ptf_weekly_prices[w])
    ptf_weekly_ln *= 100

    # Подготовка данных бенчмарка с учётом общего gagr периода
    # /////////////////////////////////////////////

    # ---
    # Цикл формирования недельных цен закрытия бенчмарка
    bench_weekly_prices = []
    for bench_date in gagr_weekly_dates:
        j, = np.where(bench_daily_dates == bench_date)[0]
        bench_weekly_prices = np.append(bench_weekly_prices, bench_daily_prices[j])

    # ---
    # Расчёт логарифмов отношения недельных цен закрытия бенчмарка
    bench_weekly_ln = ln_estimator(bench_weekly_prices)

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    # Рассчёт корреляционной матрицы, волатильности и бета-коэффициентов каждого из активов портфеля и бенчмарка

    # ---
    # Функция расчёта бета-коэффициента каждого актива с учётом отсечения данных
    def beta_estimator(as_dates, as_prices, bench_dates, bench_prices):
        """
        Функция расчёта бета-коэффициента каждого актива с учётом отсечения данных.
        :param as_dates: доступные даты актива
        :param as_prices: доступные цены актива
        :param bench_dates: доступные даты бенчмарка
        :param bench_prices: доступные цены бенчмарка
        :return beta: бета-коэффициент актива
        """

        unq_dates = np.sort(list(set(as_dates) & set(bench_dates)))
        as_dates, bench_dates = np.array(as_dates), np.array(bench_dates)
        as_prices_for_beta, bench_prices_for_beta = [], []
        for date in unq_dates:
            s1, = np.where(as_dates == date)[0]
            as_prices_for_beta = np.append(as_prices_for_beta, as_prices[s1])

            s2, = np.where(bench_dates == date)[0]
            bench_prices_for_beta = np.append(bench_prices_for_beta, bench_prices[s2])
        as_ln, bench_ln = ln_estimator(as_prices_for_beta), ln_estimator(bench_prices_for_beta)
        beta = np.cov(as_ln, bench_ln, bias=True)[0][1] / np.var(bench_ln)

        return beta

    # ---
    def volatility_estimator(as_prices):
        """
        Функция расчёта волатильности каждого актива за доступный период суцествования актива .
        !В рамках анализа портфеля (с начала анализа или позже до сегодняшнего дня).
        :param as_prices: доступные цены актива
        :return vol: годовая волатильность актива
        """

        as_ln = ln_estimator(as_prices)
        vol = np.std(as_ln) * 52 ** (1 / 2)

        return vol

    # ---
    def corr_estimator(as1_dates, as1_prices, as2_dates, as2_prices):
        """
        Функция расчёта корреляции произвольной пары активов с учётом отсечения данных.
        !В рамках анализа портфеля (с начала анализа или позже до сегодняшнего дня)

        :param as1_dates: доступные даты первого актива
        :param as1_prices: доступные цены первого актива
        :param as2_dates: доступные даты второго актива
        :param as2_prices: доступные цены второго актива
        :return corr: корреляция двух активов
        """

        unq_dates = np.sort(list(set(as1_dates) & set(as2_dates)))
        as1_dates, as2_dates = np.array(as1_dates), np.array(as2_dates)
        as1_prices_for_corr, as2_prices_for_corr = [], []
        for date in unq_dates:
            s1, = np.where(as1_dates == date)[0]
            as1_prices_for_corr = np.append(as1_prices_for_corr, as1_prices[s1])

            s2, = np.where(as2_dates == date)[0]
            as2_prices_for_corr = np.append(as2_prices_for_corr, as2_prices[s2])

        as1_ln, as2_ln = ln_estimator(as1_prices_for_corr), ln_estimator(as2_prices_for_corr)
        corr = stats.pearsonr(as1_ln, as2_ln)[0]

        return corr

    # /////////////////////////////////////////////
    # Цикл формирования недельных цен закрытия бенчмарка полного периода
    # !!! Для расчёта беты каждого актива и корреляционной матрицы
    bench_as_wkl_dates, bench_as_wkl_prices = weeks_in_range(bench_daily_dates[0], bench_daily_dates[-1]), []
    for bench_as_date in bench_as_wkl_dates:
        j, = np.where(bench_daily_dates == bench_as_date)[0]
        bench_as_wkl_prices = np.append(bench_as_wkl_prices, bench_daily_prices[j])

    # Ниже идёт формирование статистических параметров актива и бенчмарка
    vol_bench_as = volatility_estimator(bench_as_wkl_prices)  # Волатильность бенчмарка
    tickers_bench_assets = np.array([benchmark_ticker])  # Тикеры активов портфеля и бенчмарка
    vol_bench_assets = np.array([vol_bench_as])  # Волатильности активов портфеля и бенчмарка
    beta_bench_assets = np.array([1])  # Бета-коэффициенты активов потрфеля и бенчмарка (он вегда равен 1)
    corr_matrix_bench_as = [[1]]  # Корреляционная матрица активов портфеля и бенчмарка

    if ' ' not in as_after_fifo:
        # Формируем недельные доступные даты по каждому из активов из открытых позиций
        as_wkl_dates, as_wkl_prices = [[]] * open_as_cnt, [[]] * open_as_cnt
        for i in range(open_as_cnt):
            as_wkl_dates[i] = list(weeks_in_range(open_pos_start_dates[i], end_date))
            j, = np.where(as_after_fifo[i] == unqTickers)[0]
            as_wkl_prices[i] = alignment_prices(as_wkl_dates[i], ptf_daily_dates, as_daily_prices[j])

        # Расчёт волатильностей, бета-коэффициентов активов и бенчмарка с учётом доступности/пересечений дат
        vol_assets, beta_assets = [], []
        for i in range(open_as_cnt):
            if len(as_wkl_dates[i]) > 2:  # Тикеры активов портфеля и бенчмарка
                tickers_bench_assets = np.append(tickers_bench_assets, as_after_fifo[i])
                vol_tmp = volatility_estimator(as_wkl_prices[i])
                beta_tmp = beta_estimator(as_wkl_dates[i], as_wkl_prices[i], bench_as_wkl_dates, bench_as_wkl_prices)
                vol_assets = np.append(vol_assets, vol_tmp)
                beta_assets = np.append(beta_assets, beta_tmp)
        vol_bench_assets = np.append(vol_bench_assets, vol_assets)  # Волатильности активов и бенчмарка
        beta_bench_assets = np.append(beta_bench_assets, beta_assets)  # Бета-коэффициенты активов и бенчмарка

        # Расчёт корреляционной матрицы активов и бенчмарка с учётом пересечений доступных дат
        corr_matrix_bench_as = np.ones((open_as_cnt + 1, open_as_cnt + 1))
        for i in range(open_as_cnt):
            if len(as_wkl_dates[i]) > 2:
                corr_temp = corr_estimator(as_wkl_dates[i], as_wkl_prices[i], bench_as_wkl_dates, bench_as_wkl_prices)
                corr_matrix_bench_as[i + 1][0], corr_matrix_bench_as[0][i + 1] = corr_temp, corr_temp
                for j in range(open_as_cnt):
                    if j > i:
                        corr_temp = corr_estimator(as_wkl_dates[i], as_wkl_prices[i], as_wkl_dates[j], as_wkl_prices[j])
                        corr_matrix_bench_as[i + 1][j + 1], corr_matrix_bench_as[j + 1][i + 1] = corr_temp, corr_temp

        col_row = 0  # Если активы торгуются менее 3 недель, то не показываем корелляции с ними
        for i in range(open_as_cnt):
            col_row += 1
            if len(as_wkl_dates[i]) <= 2:
                corr_matrix_bench_as = np.delete(corr_matrix_bench_as, col_row, axis=0)
                corr_matrix_bench_as = np.delete(corr_matrix_bench_as, col_row, axis=1)
                col_row -= 1

    # Массив тикеров активов портфеля и бенчмарка, их волатильности и бета-коэффициенты
    vol_beta_bench_assets = np.array([tickers_bench_assets, vol_bench_assets, beta_bench_assets])

    # ---
    # Среднегодовые доходности портфеля/бенчмарка/безрисковой ставки
    # Вычисление среднегодовой доходности портфеля
    ptf_return_for_gagr = returnsPortfolioPeriod(cash_transactions, base_currency,
                                                 ptf_daily_dates, ptf_daily_prices,
                                                 forex_daily_prices_ptf, start_date,
                                                 gagr_start_date, gagr_date)
    ptf_gagr = 100 * ((1 + ptf_return_for_gagr[1][-1] / 100) ** (12 / gagr_months_cnt) - 1)  # GAGR портфеля

    # Вычисление среднегодовой доходности бенчмарка
    t1, = np.where(bench_daily_dates == gagr_start_date)[0]  # Индекс среднегодовой доходности портфеля
    t2, = np.where(bench_daily_dates == gagr_date)[0]  # Индекс среднегодовой доходности портфеля
    bench_gagr = 100 * ((bench_daily_prices[t2] / bench_daily_prices[t1]) ** (12 / gagr_months_cnt) - 1)  # GAGR бенчмарка

    # Вычисление среднегодовой доходности безрисковой ставки
    t1, = np.where(rf_daily_dates == gagr_start_date)[0]  # Индекс среднегодовой доходности портфеля
    t2, = np.where(rf_daily_dates == gagr_date)[0]  # Индекс среднегодовой доходности портфеля
    rf_gagr = 100 * ((rf_daily_prices[t2] / rf_daily_prices[t1]) ** (12 / gagr_months_cnt) - 1)  # GAGR безрисковой ставки

    # Годовые параметры портфеля
    beta_ptf = np.cov(ptf_weekly_ln, bench_weekly_ln, bias=True)[0][1] / np.var(bench_weekly_ln)  # Бета-коэффициент
    alpha_ptf = ptf_gagr - (rf_gagr + beta_ptf * (bench_gagr - rf_gagr))  # Альфа-коэффициент
    vol_ptf = np.std(ptf_weekly_ln) * 52 ** (1 / 2)  # Волатильность
    if vol_ptf != 0:  # Коэффициент Шарпа, коэффициент корреляции бенчмарка и портфеля
        sharpe_ptf = (ptf_gagr - rf_gagr) / vol_ptf
        corr_ptf = 100 * stats.pearsonr(ptf_weekly_ln, bench_weekly_ln)[0]
    else:
        sharpe_ptf = 0
        corr_ptf = 0
    r_square_ptf = 100 * (corr_ptf / 100) ** 2  # Коэфициент детерминации (R - квадрат)

    # Годовые параметры бенчмарка
    beta_bench = 1  # Бета-коэффициент
    alpha_bench = 0  # Альфа-коэффициент
    vol_bench = volatility_estimator(bench_weekly_prices)
    sharpe_bench = (bench_gagr - rf_gagr) / vol_bench  # Коэффициент Шарпа
    corr_bench = 100  # Коэффициент корреляции бенчмарка и бенчмарка
    r_square_bench = 100 * (corr_bench / 100) ** 22  # Коэфициент детерминации (R - квадрат)

    # Вывод риск-профиля портфеля
    if vol_ptf < 5:
        r_profile_name, r_profile_num = 'Консервативный', 1
    elif 5 <= vol_ptf < 10:
        r_profile_name, r_profile_num = 'Умеренно-консервативный', 2
    elif 10 <= vol_ptf < 15:
        r_profile_name, r_profile_num = 'Умеренный', 3
    elif 15 <= vol_ptf < 20:
        r_profile_name, r_profile_num = 'Умеренно-агрессивный', 4
    else:
        r_profile_name, r_profile_num = 'Агрессивный', 5
    risk_profile = [r_profile_num, r_profile_name]  # Название риск-профиля, номер риск-профиля

    # Массивы: наименования параметров (names_metrics), значений параметров портфеля (ptf_metrics),
    # значений параметров бенчмарка (bench_metrics), единиц измерения параметров (unit_metrics)
    names_metrics = np.array(['Доходность (GAGR)', 'Волатильность (σ)', 'Коэф. Шарпа (S)', 'Альфа (α)',
                              'Коэф. бета (β)', 'Коэф. корреляции', 'Коэфф. детерминации'])
    ptf_metrics = np.array([ptf_gagr, vol_ptf, sharpe_ptf, alpha_ptf, beta_ptf, corr_ptf, r_square_ptf])
    bench_metrics = np.array([bench_gagr, vol_bench, sharpe_bench, alpha_bench, beta_bench, corr_bench, r_square_bench])
    unit_metrics = np.array(['%', '%', ' ', '%', ' ', '%', '%'])

    # Для вывода статистических параметров (коэффициентов портфеля) - объект dict()
    stats_metrics = np.zeros(7, dtype=object)
    for i in range(len(names_metrics)):
        stats_metrics[i] = dict()
        stats_metrics[i]['name'], stats_metrics[i]['value_portfolio'] = names_metrics[i], ptf_metrics[i]
        stats_metrics[i]['value_benchmark'], stats_metrics[i]['unit'] = bench_metrics[i], unit_metrics[i]

    return bench_daily_dates, bench_daily_prices, rf_daily_dates, rf_daily_prices, ptf_daily_dates, \
           ptfCloseAbsDaysCurve, forex_daily_prices_ptf, start_date, freeCashVecRUB[-1], freeCashVecUSD[-1], \
           abs_profits_by_periods, openPositions, othersTemporary, startsPriceAs, weightedAvgSum, unqExfInfOut, \
           newDays, stats_metrics, corr_matrix_bench_as, vol_beta_bench_assets, risk_profile

# Примечания к выходу функции (что и какой параметр значит):
#
# --------------------
# 1) Данные для визуализации диаграммы распределения активов открытых позиций на данный момент:
# 1.1) openPositions - массив с информацией об открытых позициях
# unqEmitents - эмитенты открытых позиций
# unqAsfInfOut - тикеры активов открытых позиций
# avgByuPrices - средневзвешенная цена покупки открытых позиций
# thisPriceAs - текущая цена актива в реальный момент времени
# qualityOpen - количество каждого актива открытых позиций
# percentOfPtf - доля стоимости актива от стоимости портфеля
# startPrice - начальная стоимость актива
# thisPrice - конечная стоимость актива на данный момент
# percentChange - % изменения цены актива
# othersTemporary - массив с дополнительной информацией
# 1.2) othersTemporary - дополнительная информациря о портфеле
# totCostPtf - текущая цена портфеля
# freeCashVec[-1] - свободные деньги инвестора на данный момент
# percentOfPtfCash - % свободных денег инвестора на данный момент от стоимости портфеля
# openPositionsProfit - доходность открытых позиций на текущий момент
# returnAllRealTime - доходность портфеля в реальный момент времени
#
# --------------------
# 2) Данные для визуализации графика доходности портфеля, бенчмарка, безрисковой ставки за период
# !Стоит обратить внимание, что на сайте присутствует возможность выбора своего периода (в рамках заданных дат на входе)
# !Для этого необходимо выделить из массива дат - необходимые и соответствующие им цены.
# !Соответственно в данном случае график доходности должен будет пересчитываться как: массив цен / его нулевой элемент
# !! ТОЛЬКО для бенчмарка и безрисковой ставки (для портфеля всё рассчитано по другому)
# 2.1) Бенчмарк:
# benchDatesDays - даты цен закрытия бенчмарка
# benchCloseDays - цены закрытия бенчмарка
# 2.2) Безрисковая ставка:
# nrDatesDays - даты цен закрытия безрисковой ставки
# nrCloseDays - цены закрытия безрисковой ставки
# 2.3) Портфель (обратить внимание): - см. строку кода 386
# !!В связи со сложностью рассчёта дневных доходностей портфеля на производном периоде, написал функцию, зависящую от
# входных дат: start_chart_date, end_chart_date (данные даты должны взяты из соображений того, какой период выбрал пользователь)
# allDates - даты цен закрытия портфеля (должны выводиться только в диапазоне с start_chart_date по end_chart_date)
# ptfCloseAbsDaysCurve - цены закрытия портфеля (рассчитаны в диапазоне с start_chart_date по end_chart_date)
#
# --------------------
# 3) Абсолютные показателя за определённый период.
# !В зависимости от периода анализа портфеля
# returnArray - массив доходностей портфеля, бенчмарка, безрисковой ставки
#
# --------------------
# 4) Показатели доходности, риска, взаимосвязи инвестиционного портфеля
# statsParam - массив показателей и их названий
#
# --------------------
# 5) Матрица корреляций активов
# !Примечание: каждый тикер соответствует каждой строке/столбцу матрицы корреляций
# asCorrMatrix - корреляционная матрица активов
# asVolBeta - волатильности активов и их бета-коэфициенты, а также тикеры активов


# # Тестовые входные параметры для анализа портфеля # #

# # Массив пополнений-снятий
# arrayCash_test = []

# arrayCash_test = [['2018-01-31', 'United States Dollar', 'USD', 'Input', 20000],
#                   ['2018-01-31', 'Russian Ruble', 'RUB', 'Input', 800000],
#                   ['2018-03-26', 'United States Dollar', 'USD', 'Output', 5000],
#                   ['2018-05-15', 'Russian Ruble', 'RUB', 'Output', 300000],
#                   ['2018-05-30', 'United States Dollar', 'USD', 'Output', 2000],
#                   ['2018-06-11', 'United States Dollar', 'USD', 'Input', 3000],
#                   ['2018-07-26', 'Russian Ruble', 'RUB', 'Output', 300000]]

# arrayCash_test = [['2018-01-31', 'United States Dollar', 'USD', 'Input', 10000]]

# # Массив обмена валюты (покупка / продажа)
# arrayChange_test = []

# arrayChange_test = [['2018-02-19', 'USDRUB', 'Buy', 56.2, 2000],
#                     ['2018-04-11', 'USDRUB', 'Sell', 62.15, 1500],
#                     ['2018-06-18', 'USDRUB', 'Sell', 62.3, 1500],
#                     ['2018-07-17', 'USDRUB', 'Buy', 63.78, 2000]]

# # Массив транзакций инвестора
# arrayTickers_test = []

# arrayTickers_test = [['2018-01-31', 'Facebook', 'FB', 'NASDAQ', 'Buy', 185.67, 3],
#                      ['2018-02-01', 'Apple', 'AAPL', 'NASDAQ', 'Buy', 167.88, 3],
#                      ['2018-02-01', 'Visa', 'V', 'NYSE', 'Buy', 124.97, 8],
#                      ['2018-02-12', 'Netflix', 'NFLX', 'NASDAQ', 'Buy', 255.24, 2],
#                      ['2018-02-16', 'Facebook', 'FB', 'NASDAQ', 'Buy', 177.57, 3],
#                      ['2018-02-21', 'Albemarle', 'ALB', 'NYSE', 'Buy', 113.94, 5],
#                      ['2018-02-21', 'Starbucks', 'SBUX', 'NASDAQ', 'Buy', 56.5, 10],
#                      ['2018-02-28', 'Albemarle', 'ALB', 'NYSE', 'Buy', 102.9, 5],
#                      ['2018-03-14', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Buy', 75.1, 8],
#                      ['2018-03-19', 'Facebook', 'FB', 'NASDAQ', 'Buy', 171.79, 3],
#                      ['2018-03-19', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Buy', 70.41, 8],
#                      ['2018-03-19', 'Albemarle', 'ALB', 'NYSE', 'Buy', 96.2, 5],
#                      ['2018-03-26', 'Micron', 'MU', 'NASDAQ', 'Buy', 54.73, 10],
#                      ['2018-03-26', 'Boeing', 'BA', 'NYSE', 'Buy', 327.29, 2],
#                      ['2018-04-25', 'Micron', 'MU', 'NASDAQ', 'Buy', 47.45, 10],
#                      ['2018-04-25', 'Square', 'SQ', 'NYSE', 'Buy', 44.71, 12],
#                      ['2018-05-02', 'Square', 'SQ', 'NYSE', 'Buy', 49.40, 12],
#                      ['2018-07-23', 'Square', 'SQ', 'NYSE', 'Sell', 71.71, 24],
#                      ['2018-07-24', 'Boeing', 'BA', 'NYSE', 'Sell', 356.68, 2],
#                      ['2018-07-24', 'Facebook', 'FB', 'NASDAQ', 'Sell', 213.6, 9],
#                      ['2018-07-24', 'Apple', 'AAPL', 'NASDAQ', 'Sell', 192.83, 3],
#                      ['2018-08-07', 'Albemarle', 'ALB', 'NYSE', 'Buy', 93.21, 5],
#                      ['2018-08-30', 'Electronic Arts', 'EA', 'NASDAQ', 'Buy', 116.41, 5],
#                      ['2018-09-11', 'Micron', 'MU', 'NASDAQ', 'Buy', 43.46, 15],
#                      ['2018-09-12', 'Facebook', 'FB', 'NASDAQ', 'Buy', 161.98, 5],
#                      ['2018-09-28', 'Facebook', 'FB', 'NASDAQ', 'Buy', 167.67, 5],
#                      ['2018-10-16', 'Netflix', 'NFLX', 'NASDAQ', 'Buy', 338.32, 2],
#                      ['2018-10-16', 'Electronic Arts', 'EA', 'NASDAQ', 'Buy', 107.59, 5],
#                      ['2018-10-17', 'Square', 'SQ', 'NYSE', 'Buy', 76.71, 8],
#                      ['2018-11-08', 'Starbucks', 'SBUX', 'NASDAQ', 'Sell', 68.75, 10],
#                      ['2018-11-12', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Buy', 54.26, 13],
#                      ['2019-02-05', 'Netflix', 'NFLX', 'NASDAQ', 'Sell', 356.56, 4],
#                      ['2019-05-08', 'Albemarle', 'ALB', 'NYSE', 'Buy', 72.84, 8],
#                      ['2019-07-24', 'Facebook', 'FB', 'NASDAQ', 'Sell', 201.17, 10],
#                      ['2019-08-02', 'Square', 'SQ', 'NYSE', 'Buy', 68.5, 8],
#                      ['2019-08-09', 'Valero Energy', 'VLO', 'NYSE', 'Buy', 79.1, 10],
#                      ['2019-09-10', 'Square', 'SQ', 'NYSE', 'Buy', 61.23, 10],
#                      ['2019-09-10', 'CVS Health', 'CVS', 'NYSE', 'Buy', 63.05, 5],
#                      ['2020-04-20', 'Valero Energy', 'VLO', 'NYSE', 'Buy', 51.98, 11],
#                      ['2020-06-03', 'Micron', 'MU', 'NASDAQ', 'Sell', 48.09, 35],
#                      ['2020-06-03', 'Albemarle', 'ALB', 'NYSE', 'Sell', 79.72, 28],
#                      ['2020-06-03', 'Square', 'SQ', 'NYSE', 'Sell', 90.88, 26],
#                      ['2020-06-03', 'Electronic Arts', 'EA', 'NASDAQ', 'Sell', 118.65, 10],
#                      ['2020-06-03', 'Activision Blizzard', 'ATVI', 'NASDAQ', 'Sell', 70.17, 29],
#                      ['2020-06-03', 'CVS Health', 'CVS', 'NYSE', 'Sell', 66.68, 5],
#                      ['2020-06-03', 'Valero Energy', 'VLO', 'NYSE', 'Sell', 69.32, 21],
#                      ['2020-06-03', 'Visa', 'V', 'NYSE', 'Sell', 196.25, 8]]
#
# # Массив дивидендов активов инвестора
# arrayDividends_test = []

# arrayDividends_test = [['2018-02-15', 'Facebook', 'FB', 'NASDAQ', 'Dividend', 3.67],
#                        ['2018-02-15', 'Netflix', 'NFLX', 'NASDAQ', 'Dividend', 6.24]]

# !!!При изменении валюты анализа портфеля, необходимо менять бенчмарк и безрисковую ставку
# forexTr_test = "USD"
# benchTicker_test, benchExchange_test = "GSPC", "INDX"
# nonRiskTicker_test, nonRiskExchange_test = "IDCOT10TR", "INDX"
# startDateCurve_test, endDateCurve_test = 'None', 'None'

# startDateCurve_test, endDateCurve_test = '2018-05-01', '2020-02-11'

# test = analysingPortfolio(arrayTickers_test, arrayCash_test, arrayChange_test, arrayDividends_test,
#                           benchTicker_test, benchExchange_test,
#                           nonRiskTicker_test, nonRiskExchange_test,
#                           forexTr_test, startDateCurve_test, endDateCurve_test)

# test = analysingPortfolio([['2020-07-02', 'Sberbank of Russia', 'SBER', 'MCX', 'Buy', 280.0, 10000.0],
#                            ['2020-10-02', 'Sberbank of Russia', 'SBER', 'MCX', 'Sell', 230.0, 10000.0]],
#                           [['2020-04-06', 'Russian Ruble', 'RUB', 'Input', 10000000.0]],
#                           [['2020-07-02', 'USDRUB', 'Buy', 70.0, 20000.0]], [],
#                           '0O7N', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')

# test = analysingPortfolio([['2020-12-03', 'Pro Shares UltraPro QQQ', 'TQQQ', 'NYSE ARCA', 'Buy', 169.995, 16],
#                            ['2020-12-03', 'Pro Shares Ultra SP500', 'SSO', 'NYSE ARCA', 'Buy', 72.35, 38],
#                            ['2020-12-03', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Buy', 12.32, 227],
#                            ['2020-12-03', 'Pro Shares Ultra SP500', 'SSO', 'NYSE ARCA', 'Buy', 87.81, 127],
#                            ['2020-10-15', 'Pro Shares Ultra QQQ', 'QLD', 'NYSE ARCA', 'Buy', 99.32, 135],
#                            ['2020-10-15', 'Pro Shares Ultra SP500', 'SSO', 'NYSE ARCA', 'Buy', 79.175, 35],
#                            ['2020-10-15', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Buy', 38.47, 240],
#                            ['2020-06-03', 'Pro Shares UltraPro Dow30', 'UDOW', 'NYSE ARCA', 'Sell', 66.31, 374],
#                            ['2020-06-03', 'Pro Shares UltraPro QQQ', 'TQQQ', 'NYSE ARCA', 'Sell', 86.08, 209],
#                            ['2020-06-03', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Sell', 38.13, 207],
#                            ['2020-04-03', 'iShares Gold Trust', 'IAU', 'NYSE ARCA', 'Buy', 15.46, 231],
#                            ['2020-04-03', 'Pro Shares UltraPro Dow30', 'UDOW', 'NYSE ARCA', 'Buy', 36.385, 9],
#                            ['2020-04-03', 'Pro Shares UltraPro QQQ', 'TQQQ', 'NYSE ARCA', 'Buy', 41.75, 9],
#                            ['2020-04-03', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Sell', 45.65, 94],
#                            ['2020-03-11', 'Pro Shares UltraPro Dow30', 'UDOW', 'NYSE ARCA', 'Buy', 66.28, 365],
#                            ['2020-03-11', 'Pro Shares UltraPro QQQ', 'TQQQ', 'NYSE ARCA', 'Buy', 62.07, 200],
#                            ['2020-03-11', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Buy', 43.85, 301]],
#                            [['2020-03-11', 'United States Dollar', 'USD', 'Input', 50000]], [], [],
#                            'SP500TR', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
#
# print(test)

# test = analysingPortfolio([['2020-06-03', 'Direxion Daily S&P500® Bull 3X Shares', 'SPXL', 'NYSE ARCA', 'Sell', 43.46, 443],
#                            ['2020-06-03', 'Direxion Daily 20+ Year Treasury Bull 3X Shares', 'TMF', 'NYSE ARCA', 'Sell', 37.70, 130],
#                            ['2020-06-03', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Sell', 11.7, 292],
#                            ['2020-04-03', 'Direxion Daily S&P500® Bull 3X Shares', 'SPXL', 'NYSE ARCA', 'Buy', 23.81, 238],
#                            ['2020-04-03', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Buy', 6.59, 205],
#                            ['2020-04-03', 'iShares Gold Trust', 'IAU', 'NYSE ARCA', 'Sell', 15.41, 23],
#                            ['2020-04-03', 'Direxion Daily 20+ Year Treasury Bull 3X Shares', 'TMF', 'NYSE ARCA', 'Sell', 45.23, 149],
#                            ['2019-12-27', 'Direxion Daily S&P500® Bull 3X Shares', 'SPXL', 'NYSE ARCA', 'Buy', 67.39, 205],
#                            ['2019-12-27', 'Direxion Daily 20+ Year Treasury Bull 3X Shares', 'TMF', 'NYSE ARCA', 'Buy', 26.96, 279],
#                            ['2019-12-27', 'iShares Gold Trust', 'IAU', 'NYSE ARCA', 'Buy', 14.45, 86],
#                            ['2019-12-27', 'Direxion Daily MSCI Real Est Bull 3X Shares', 'DRN', 'NYSE ARCA', 'Buy', 28.59, 87]],
#                           [['2019-12-27', 'United States Dollar', 'USD', 'Input', 25067]], [], [], 'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')

# arrayTickers_test = [['2020-11-19', 'Olema Pharmaceuticals Inc', 'OLMA', 'NASDAQ', 'Buy', 46.21, 20],
#                      ['2020-11-19', 'Zanite Acquisition Corp', 'ZNTEU', 'NASDAQ', 'Buy', 10.05, 100],
#                      ['2020-11-16', 'Dragoneer Growth Opportunities II', 'DGNS', 'NASDAQ', 'Buy', 10, 100],
#                      ['2020-10-20', 'Goodrx Holdings Inc', 'GDRX', 'NASDAQ', 'Buy', 48.83, 20],
#                      ['2020-09-03', 'Bctg Acquisition Corp', 'BCTG', 'NASDAQ', 'Buy', 9.91, 112]]
#

# test = analysingPortfolio([['2020-12-11', 'Uber Inc', 'UBER', 'NASDAQ', 'Buy', 52.33, 30],
#                            ['2020-12-11', 'Uber Inc', 'UBER', 'NASDAQ', 'Sell', 200, 30]],
#                           [['2020-12-11', 'United States Dollar', 'USD', 'Input', 1800]], [], [],
#                           'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
# print(test)


# test = analysingPortfolio([['2020-12-16', 'SBER Etf', 'SBMX', 'MCX', 'Buy', 1500, 4]],
#                           [['2020-12-15', 'Russian Ruble', 'RUB', 'Input', 6231.6]], [], [],
#                           'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
# print(test)


# test = analysingPortfolio([['2010-02-11', 'Apple Inc', 'AAPL', 'NASDAQ', 'Buy', 207.72, 30]],
#                           [['2010-02-11', 'United States Dollar', 'USD', 'Input', 6231.6]], [], [],
#                            'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
# print(test)


# test = analysingPortfolio([['2020-12-03', 'Apple Inc', 'AAPL', 'NASDAQ', 'Buy', 122, 1]],
#                           [['2020-12-03', 'United States Dollar', 'USD', 'Input', 122]], [], [],
#                           'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
# print(test)


# test = analysingPortfolio([['2020-12-09', 'Airbnb', 'ABNB', 'NASDAQ', 'Buy', 68, 1],
#                            ['2020-12-10', 'Hhhhhyyymmm', 'HYFM', 'NASDAQ', 'Buy', 68, 1]],
#                           [['2020-05-04', 'United States Dollar', 'USD', 'Input', 500]], [], [],
#                           'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
# print(test)


# arrayCash_test = [['2010-03-12', 'United States Dollar', 'USD','Input', 2000],
#                   ['2010-03-12', 'Russian Ruble', 'RUB', 'Input', 180000],
#                   ['2011-03-28', 'Russian Ruble', 'RUB', 'Output', 100000],
#                   ['2011-10-11', 'United States Dollar', 'USD','Input', 2000],
#                   ['2011-10-11', 'Russian Ruble', 'RUB', 'Input', 150000],
#                   ['2014-04-30', 'Russian Ruble', 'RUB', 'Input', 100000],
#                   ['2014-12-18', 'United States Dollar', 'USD', 'Input', 3000],
#                   ['2014-12-18', 'Russian Ruble', 'RUB', 'Input', 200000],
#                   ['2018-11-28', 'Russian Ruble', 'RUB', 'Output', 350000],
#                   ['2018-11-28', 'United States Dollar', 'USD', 'Input', 2500],
#                   ['2020-08-28', 'Russian Ruble', 'RUB', 'Output', 600000],
#                   ['2020-08-28', 'United States Dollar', 'USD', 'Output', 90000]]
#
#
# arrayTickers_test = [['2010-03-12', 'Apple', 'AAPL', 'NASDAQ', 'Buy', 225, 4],
#                      ['2010-03-17', 'Advanced Micro', 'AMD', 'NASDAQ', 'Buy', 9.5, 100],
#                      ['2010-03-30', 'Sberbank', 'SBER', 'MCX', 'Buy', 84, 1000],
#                      ['2010-03-30', 'Lukoil', 'LKOH', 'MCX', 'Buy', 1660, 50],
#                      ['2011-03-28', 'Lukoil', 'LKOH', 'MCX', 'Sell', 2000, 50],
#                      ['2012-01-17', 'Apple', 'AAPL', 'NASDAQ', 'Buy', 420, 2],
#                      ['2012-01-17', 'Lukoil', 'LKOH', 'MCX', 'Buy', 1780, 80],
#                      ['2013-11-29', 'Apple', 'AAPL', 'NASDAQ', 'Sell', 550, 3],
#                      ['2014-04-30', 'Sberbank', 'SBER', 'MCX', 'Buy', 71, 1000],
#                      ['2015-01-01', 'Apple', 'AAPL', 'NASDAQ', 'Buy', 110, 20],
#                      ['2015-01-08', 'Sberbank', 'SBER', 'MCX', 'Buy', 65, 1000],
#                      ['2016-01-20', 'Advanced Micro', 'AMD', 'NASDAQ', 'Buy', 1.78, 1000],
#                      ['2016-08-16', 'Sberbank', 'SBER', 'MCX', 'Sell', 138.1, 500],
#                      ['2016-10-11', 'Lukoil', 'LKOH', 'MCX', 'Sell', 3100, 30],
#                      ['2017-08-25', 'Sberbank', 'SBER', 'MCX', 'Sell', 180, 500],
#                      ['2018-11-28', 'Advanced Micro', 'AMD', 'NASDAQ', 'Sell', 21, 100],
#                      ['2018-11-28', 'Lukoil', 'LKOH', 'MCX', 'Sell', 4700, 30],
#                      ['2020-03-23', 'Sberbank', 'SBER', 'MCX', 'Buy', 183, 500],
#                      ['2020-03-23', 'Advanced Micro', 'AMD', 'NASDAQ', 'Buy', 41, 100],
#                      ['2020-03-23', 'Lukoil', 'LKOH', 'MCX', 'Buy', 4100, 20],
#                      ['2020-03-23', 'Apple', 'AAPL', 'NASDAQ', 'Buy', 224, 10],
#                      ['2020-08-27', 'Sberbank', 'SBER', 'MCX', 'Sell', 227, 2500],
#                      ['2020-08-27', 'Advanced Micro', 'AMD', 'NASDAQ', 'Sell', 82, 1100]]

# test = analysingPortfolio(arrayTickers_test, arrayCash_test, [], [], 'GSPC', 'INDX', 'IDCOT10TR', 'INDX', 'USD', 'None', 'None')
#
# print(test)