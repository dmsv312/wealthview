import os
from celery import Celery
from celery.schedules import crontab
from kombu.serialization import register

from algorithm import serializers

register('custom_json', serializers.custom_dumps, serializers.custom_loads,
         content_type='application/x-custom_json',
         content_encoding='utf-8')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WealthView.settings")

app = Celery('WealthView')
app.config_from_object('django.conf:settings', namespace='CELERY')


app.conf.beat_schedule = {
    'parse_assets': {
        'task': 'backtest.tasks.parse_assets',
        'schedule': crontab(hour=1, minute=30),
    },
    'update_attribs': {
        'task': 'backtest.tasks.update_attribs',
        'schedule': crontab(minute='*/30'),
    },
    'reparse_users_attribs': {
        'task': 'backtest.tasks.reparse_users_attribs',
        'schedule': crontab(hour=1, minute=45),
    },
    'bot_notify': {
        'task': 'core.tasks.bot_notify',
        'schedule': crontab(hour='10-21', minute='*/5'),
    },
    'bot_notify_reset': {
        'task': 'core.tasks.bot_notify_reset',
        'schedule': crontab(hour=9, minute=45),
    },
    'update_profiles': {
        'task': 'backtest.tasks.update_bot_profiles',
        'schedule': crontab(hour=2, minute=30),
    }
}
app.conf.timezone = 'Europe/Moscow'

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


def celery_is_running(app=app):
    if not app.control.inspect().stats():
        return False
    return True
