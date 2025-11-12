from datetime import datetime, timedelta
import numpy as np


# error - возвращаемый алгоритмом ЛК текст ошибки
def check_errors_dictionary(error):
    """Проверяет возвращаемую из ЛК ошибку на корректность из всего списка ошибок."""
    errors_dict = ["Установите рабочий день для совершения операции", "Невозможно добавить транзакцию с датой ранее",
                   "Учёт «коротких» позиций (маржинальных сделок) невозможен. Установите меньшее количество актива",
                   "Недостаточно средств"]
    for error_text in errors_dict:
        if error_text in error:
            return True
    return False


# start_date - стартовая дата анализа портфеля
# end_date - конечная дата анализа портфеля
def days_in_range(start_date, end_date):
    """Формирует массив дневных дат в диапазоне (все даты кроме выходных)."""
    temp_date, date_format, all_dates_days = start_date, '%Y-%m-%d', []
    while temp_date <= end_date:
        temp_date = datetime.strptime(temp_date, date_format)
        if temp_date.weekday() not in [5, 6]:
            temp_date = datetime.strftime(temp_date, date_format)
            all_dates_days = np.append(all_dates_days, temp_date)
            temp_date = datetime.strptime(temp_date, date_format)
        temp_date = temp_date + timedelta(days=+ 1)
        temp_date = datetime.strftime(temp_date, date_format)

    return all_dates_days


# start_date - input start date (стартовая дата анализа портфеля)
# end_date - input end date (конечная дата анализа портфеля)
def weeks_in_range(start_date, end_date):
    """Формирует массив недельных дат в диапазоне (все пятницы)."""
    temp_date, date_format, all_dates_weeks = start_date, '%Y-%m-%d', []
    while temp_date <= end_date:
        temp_date = datetime.strptime(temp_date, date_format)
        if temp_date.weekday() == 4:
            temp_date = datetime.strftime(temp_date, date_format)
            all_dates_weeks = np.append(all_dates_weeks, temp_date)
            temp_date = datetime.strptime(temp_date, date_format)
        temp_date = temp_date + timedelta(days=+ 1)
        temp_date = datetime.strftime(temp_date, date_format)

    return all_dates_weeks


# start_date - input start date (стартовая дата анализа портфеля)
# end_date - input end date (конечная дата анализа портфеля)
def months_in_range(start_date, end_date):
    """Формирует массив месячных дат в диапазоне (первые числа каждого месяца)."""
    temp_date, date_format, all_dates_months = start_date, '%Y-%m-%d', []
    while temp_date <= end_date:
        temp_date = datetime.strptime(temp_date, '%Y-%m-%d')
        temp_date = temp_date.replace(day=28) + timedelta(days=4)
        temp_date = temp_date - timedelta(days=temp_date.day)
        temp_date = datetime.strftime(temp_date, '%Y-%m-%d')
        all_dates_months = np.append(all_dates_months, temp_date)
        temp_date = datetime.strptime(temp_date, '%Y-%m-%d')
        temp_date = temp_date + timedelta(days=+ 1)
        temp_date = datetime.strftime(temp_date, '%Y-%m-%d')

    return all_dates_months


# ------------------ Вспомогательные функции ------------------
# array - входной массив для транспонирования
def transpose(array):
    """Функция транспонирования произвольной матрицы."""
    tr_array = [list(element) for element in zip(*array)]
    return tr_array


# array_dates - входной массив дат
# date  - дата, в которой нам необходимо найти цену закрытия
def search_date(array_dates, date, symbol):
    """Функция поиска ближайшей последней даты в случае её отсутствия в массиве (день, когда биржа закрыта)."""
    while not (date in array_dates):
        date = datetime.strptime(date, '%Y-%m-%d')
        if symbol == "+":
            date = date + timedelta(days=+ 1)
        else:
            date = date - timedelta(days=+ 1)
        date = datetime.strftime(date, '%Y-%m-%d')
    return date


# forex - валюта для анализа портфеля: доллар США - USD или Российский рубль - RUB
# exchange - биржа актива
# asset_prices - входной массив цен закрытия актива
# forex_prices - входной массив цен закрытия курса валюты USD/RUB
def forex_conversion(forex, exchange, asset_prices, forex_prices):
    """Функция конверации цен активов в валюту анализа портфеля."""
    if exchange == ' ':
        return asset_prices

    if forex == "USD" and exchange == "MCX":
        asset_prices /= forex_prices
    elif forex == "RUB" and exchange != "MCX":
        asset_prices *= forex_prices
    return asset_prices


# !Примечание: данную функцию используем после конвертации цен актива в валюту анализа портфеля
# array_prices - входной массив цен закрытия любого актива
def ln_estimator(array_prices):
    """Функция рассчёта логарифмов отношения цен массива."""
    i, ln_prices = 1, [0]
    while i < len(array_prices):
        ln_prices = np.append(ln_prices, 100 * np.log(array_prices[i] / array_prices[i - 1]))
        i += 1

    return ln_prices


# array_dates - исходные даты в рамках анализа портфеля (все будние дни)
# asset_dates - даты цен закрытия актива
# asset_prises - цены закрытия актива
def alignment_prices(array_dates, asset_dates, asset_prises):
    """Функция выравнивая дневных цен закрытия актива в рамках аналзиа портфеля."""
    days_period, prices, day_period, day_asset = len(array_dates), [], 0, 0
    while (day_period < days_period) and (day_asset < len(asset_dates)):
        if array_dates[day_period] == asset_dates[day_asset]:
            prices = np.append(prices, asset_prises[day_asset])
            day_period += 1
            day_asset += 1
        elif array_dates[day_period] < asset_dates[day_asset]:
            prices = np.append(prices, asset_prises[day_asset - 1])
            day_period += 1
        else:
            day_asset += 1

    if array_dates[-1] > asset_dates[-1]:
        while days_period > len(prices):
            prices = np.append(prices, asset_prises[-1])

    return prices
