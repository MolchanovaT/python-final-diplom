# Указываем базовый образ
FROM python:3.11

# Устанавливаем рабочую директорию в корень проекта
WORKDIR /app

# Копируем весь проект в контейнер
COPY . /app

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Устанавливаем переменную окружения для Django
ENV DJANGO_SETTINGS_MODULE=reference.netology_pd_diplom.netology_pd_diplom.settings
ENV PYTHONPATH="/app/reference"

# Выполняем миграции, сбор статических файлов и запускаем сервер
CMD ["sh", "-c", "python /app/reference/netology_pd_diplom/manage.py migrate && python /app/reference/netology_pd_diplom/manage.py collectstatic --noinput && python /app/reference/netology_pd_diplom/manage.py runserver 0.0.0.0:8000"]
