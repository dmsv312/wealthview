#!/usr/bin/env python
import datetime
import os
import time
import sentry_sdk

import requests
import telebot
from telebot import types

WEB_API_HOST = os.getenv('WEB_HOST', 'http://127.0.0.1:8000')
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_SECRET = os.getenv('BOT_SECRET')

SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(SENTRY_DSN, traces_sample_rate=1.0)


bot = telebot.TeleBot(BOT_TOKEN, threaded=False)


PORTFOLIO_LIST = 'Мои портфели'
SUPPORT = 'Поддержка'
NOTIFICATIONS = 'Уведомления'


def get_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*[types.KeyboardButton(name) for name in [PORTFOLIO_LIST, NOTIFICATIONS]])
    keyboard.add(*[types.KeyboardButton(name) for name in [SUPPORT]])
    return keyboard


def send_to_chat(chat_id, message):
    bot.send_message(chat_id, message)


def get_user_by_token(token, chat_id):
    api_host_get = f'{WEB_API_HOST}/api/profile/?tg_token={token}'
    api_host_patch = f'{WEB_API_HOST}/api/profile/edit/?tg_token={token}'

    response = requests.get(api_host_get)
    if response.status_code == 200:
        patch_response = requests.patch(api_host_patch, {'tg_chat_id': chat_id, 'send_notify_dividends': True, 'send_notify_report_date': True})
        assert patch_response.status_code == 200
    elif response.status_code == 404:
        patch_response = requests.patch(api_host_patch, {'tg_chat_id': '', 'send_notify_dividends': False, 'send_notify_report_date': False})
        assert patch_response.status_code == 200
    else:
        raise Exception(f'wrong status code: {response.status_code}')

    response_json = response.json()
    if not response_json:
        patch_response = requests.patch(api_host_patch, {'tg_chat_id': '', 'send_notify_dividends': False, 'send_notify_report_date': False})
        assert patch_response.status_code == 200

    return response_json[0]


def get_user_by_chat_id(chat_id):
    try:
        response = requests.get(f'{WEB_API_HOST}/api/profile/initial_data/?secret={BOT_SECRET}&tg_chat_id={chat_id}')
        if response.status_code != 200:
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_site = types.InlineKeyboardButton(text='Перейти в личный кабинет', url=f'{WEB_API_HOST}/account/change_user_settings/')
            markup.add(btn_site)
            if response.status_code == 404:
                bot.send_message(chat_id, 'Произошла ошибка при получении данных, переподключите бота в личном кабинете', reply_markup=markup)
            else:
                bot.send_message(chat_id, 'Произошла ошибка при получении данных, попробуйте позже')
                response.raise_for_status()
        return response.json()
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        bot.send_message(chat_id, 'Произошла ошибка при получении данных, попробуйте позже')


def get_portfolios(chat_id):
    user = get_user_by_chat_id(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    portfolios = user['portfolios']['data']
    if portfolios:
        markup.add(
            *[
                types.InlineKeyboardButton(text=portfolio_data['name'], callback_data=f"{portfolio_data['id']}")
                for portfolio_id, portfolio_data
                in portfolios.items()
            ]
        )
        bot.send_message(chat_id, 'Выберите портфель', reply_markup=markup)
    else:
        bot.send_message(chat_id, 'У вас пока нет портфелей.', reply_markup=markup)


def get_notification_types(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(*[
        #types.InlineKeyboardButton(text='Всё сразу', callback_data=f"notify_all"),
        types.InlineKeyboardButton(text='Дивиденды', callback_data=f"notify_dividends"),
        types.InlineKeyboardButton(text='Отчетность', callback_data=f"notify_reports"),
    ])
    bot.send_message(chat_id, 'Выберите тип уведомления', reply_markup=markup)


@bot.message_handler(commands=["start"])
def start(message):
    cmd, *token = message.html_text.split()

    try:
        token = str(token[0])
    except IndexError:
        token = ''

    if not token:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*[types.KeyboardButton(name) for name in ['Перейти на сайт']])

        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_site = types.InlineKeyboardButton(text='Перейти на сайт', url=f'{WEB_API_HOST}/')
        markup.add(btn_site)
        bot.send_message(message.chat.id, "Перейти на сайт для регистрации.", reply_markup=markup)

        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_site = types.InlineKeyboardButton(text='Перейти в личный кабинет', url=f'{WEB_API_HOST}/account/change_user_settings/')
        markup.add(btn_site)
        bot.send_message(message.chat.id, "Если у Вас уже есть аккаунт, то подключитесь к боту через ссылку в личном кабинете.", reply_markup=markup)

    else:
        get_user_by_token(token, message.chat.id)
        menu_keyboard = get_menu_keyboard()
        bot.send_message(
            message.chat.id,
            'Привет! 👋🏼 Это бот веб-сервиса wealthview.ru\nМы научили его делать отчет по результатам твоих портфелей, а еще уведомлять о ближайших дивидендах и отчетностях. Напиши в поддержку WealthView, если есть вопросы или пожелания.',
            reply_markup=menu_keyboard
        )

        get_portfolios(message.chat.id)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id

    user_data = get_user_by_chat_id(chat_id)

    if 'notify_' in call.data:
        if '-' in call.data:
            _, notify_type_with_id = call.data.split('_')
            notify_type, portfolio_id = notify_type_with_id.split('-')

            if portfolio_id == 'all':
                # в первом портфеле есть инфа по всем портфелям(не баг, а фича)
                portfolios = [user_data['portfolios']['total_data']]
            else:
                portfolios = [user_data['portfolios']['data'][portfolio_id]]

            message = ''
            for portfolio in portfolios:
                if notify_type == 'all':
                    if portfolio_id == 'all':
                        message += portfolio['all_dividends_text']
                        message += portfolio['all_reports_text']
                    else:
                        message += portfolio['dividends_text']
                        message += portfolio['reports_text']

                if notify_type == 'dividends':
                    if portfolio_id == 'all':
                        message += portfolio['all_dividends_text']
                    else:
                        message += portfolio['dividends_text']
                if notify_type == 'reports':
                    if portfolio_id == 'all':
                        message += portfolio['all_reports_text']
                    else:
                        message += portfolio['reports_text']

            if not message:
                message = 'Нет данных'
            bot.send_message(chat_id, message, parse_mode='html')

        else:
            _, notify_type = call.data.split('_')

            user = get_user_by_chat_id(chat_id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            portfolios = user['portfolios']['data']
            if portfolios:
                markup.add(
                    *[
                         types.InlineKeyboardButton(text='Все портфели', callback_data=f"notify_{notify_type}-all")
                     ] + [
                         types.InlineKeyboardButton(text=portfolio_data['name'],
                                                    callback_data=f"notify_{notify_type}-{portfolio_data['id']}")
                         for portfolio_id, portfolio_data
                         in portfolios.items()
                     ]
                )
                bot.send_message(chat_id, 'Выберите портфель', reply_markup=markup)
            else:
                bot.send_message(chat_id, 'У вас пока нет портфелей.', reply_markup=markup)

    else:
        portfolio_id = call.data

        portfolio_text = user_data['portfolios']['data'][portfolio_id]['text']

        bot.send_message(chat_id, portfolio_text, parse_mode="html")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    chat_id = message.chat.id
    if message.text == PORTFOLIO_LIST:
        get_portfolios(chat_id)
    elif message.text == SUPPORT:
        bot.send_message(chat_id, "Напишите нам свой вопрос @WealthView")
    elif message.text == NOTIFICATIONS:
        get_notification_types(chat_id)
    else:
        bot.send_message(chat_id, get_user_by_chat_id(chat_id)['portfolios']['data'][message.text], parse_mode="html")

    # bot.send_message(chat_id, 'Обновленное меню', reply_markup=get_menu_keyboard())


if __name__ == '__main__' and BOT_TOKEN:
    while True:
        try:
            print('bot start polling at %s' % datetime.datetime.now())
            bot.polling(none_stop=True)
            break
        except Exception as e:
            print(e)
            sentry_sdk.capture_exception(e)
            time.sleep(3)
