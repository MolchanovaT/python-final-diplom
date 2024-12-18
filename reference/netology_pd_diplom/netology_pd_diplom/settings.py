"""
Django settings for netology_pd_diplom project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from decouple import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '=hs6$#5om031nujz4staql9mbuste=!dc^6)4opsjq!vvjxzj@'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'baton',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'django_rest_passwordreset',
    'drf_spectacular',
    'social_django',
    'backend',
    'baton.autodiscover',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'netology_pd_diplom.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'backend/templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'netology_pd_diplom.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'TEST': {
            'NAME': ':memory:',  # Используем базу в памяти для тестов
        },
    }

}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

AUTH_USER_MODEL = 'backend.User'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_USE_TLS = True

EMAIL_HOST = 'smtp.mail.ru'

EMAIL_HOST_USER = 'netology.diplom@mail.ru'
EMAIL_HOST_PASSWORD = 'CLdm7yW4U9nivz9mbexu'
EMAIL_PORT = '465'
EMAIL_USE_SSL = True
SERVER_EMAIL = EMAIL_HOST_USER

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 40,

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',

    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (

        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',  # Для анонимных пользователей
        'rest_framework.throttling.UserRateThrottle',  # Для аутентифицированных пользователей
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',  # 10 запросов в минуту для анонимных пользователей
        'user': '100/hour',  # 100 запросов в час для аутентифицированных пользователей
    },
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',  # Для Google
    # 'social_core.backends.facebook.FacebookOAuth2',  # Для Facebook
)

# Указываем URL-ы перенаправления после успешного/неуспешного логина
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = config('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')

# SOCIAL_AUTH_FACEBOOK_KEY = 'ВАШ_FACEBOOK_APP_ID'
# SOCIAL_AUTH_FACEBOOK_SECRET = 'ВАШ_FACEBOOK_APP_SECRET'

SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_EXCEPTION_HANDLER = 'backend.views.social_auth_exception_handler'
# LOGIN_REDIRECT_URL = '/auth/complete/'  # Этот URL вызовет обработчик `social_auth_complete`.

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Настройки Celery
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_TIMEZONE = 'UTC'

SPECTACULAR_SETTINGS = {
    'TITLE': 'API для проекта интернет магазина',
    'DESCRIPTION': 'Документация OpenAPI, сгенерированная с помощью DRF-Spectacular',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

BATON = {
    'SITE_HEADER': 'Моя админка',
    'SITE_TITLE': 'Моя админка',
    'INDEX_TITLE': 'Добро пожаловать в админку',
    'SUPPORT_HREF': 'molchanovatatiana33@gmail.com',
    'COPYRIGHT': 'Copyright © 2024 by Molchanova Tatiana',
    'POWERED_BY': 'Molchanova Tatiana',
}
