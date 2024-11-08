from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Устанавливаем default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netology_pd_diplom.settings')

app = Celery('netology_pd_diplom')

# Используем строку для настройки брокера
app.config_from_object('django.conf:settings', namespace='CELERY')

# Загружаем задачи из всех зарегистрированных Django приложений
app.autodiscover_tasks()
