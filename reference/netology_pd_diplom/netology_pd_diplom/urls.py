"""netology_pd_diplom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from backend.views import run_task_view, social_auth_complete

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/run_task/<int:shop_id>/', run_task_view, name='run_task_view'),
    # Социальная авторизация
    path('auth/', include('social_django.urls', namespace='social')),
    path('auth/complete/', social_auth_complete, name='social-auth-complete'),
    # Основное API
    path('api/v1/', include('backend.urls')),
]

