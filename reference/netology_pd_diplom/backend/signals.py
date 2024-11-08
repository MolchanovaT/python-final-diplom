from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import send_password_reset_token, send_registration_confirmation, send_new_order_notification
from backend.models import User

new_user_registered = Signal()

new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля.
    """
    send_password_reset_token.delay(reset_password_token)  # Используем Celery для отправки письма


@receiver(post_save, sender=User)
def new_user_registered_signal(sender, instance, created, **kwargs):
    """
    Отправляем письмо с подтверждением регистрации.
    """
    if created and not instance.is_active:
        send_registration_confirmation.delay(instance)  # Используем Celery для отправки письма


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Отправляем письмо при изменении статуса заказа.
    """
    send_new_order_notification.delay(user_id)  # Используем Celery для отправки письма
