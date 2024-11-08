from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import ConfirmEmailToken, User
from celery import shared_task
from django.core.validators import URLValidator
from requests import get
import yaml
from backend.models import Shop, Category, ProductInfo, Product, Parameter, ProductParameter, TaskStatus


@shared_task
def send_email(subject, message, recipient_email):
    """
    Отправка email с использованием Celery.
    """
    msg = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.EMAIL_HOST_USER,
        to=[recipient_email]
    )
    msg.send()


@shared_task
def send_password_reset_token(reset_password_token):
    """
    Отправка email с токеном для сброса пароля.
    """
    send_email(
        subject=f"Password Reset Token for {reset_password_token.user}",
        message=reset_password_token.key,
        recipient_email=reset_password_token.user.email
    )


@shared_task
def send_registration_confirmation(instance):
    """
    Отправка email с подтверждением регистрации.
    """
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
    send_email(
        subject=f"Password Reset Token for {instance.email}",
        message=token.key,
        recipient_email=instance.email
    )


@shared_task
def send_new_order_notification(user_id):
    """
    Отправка email с уведомлением об обновлении заказа.
    """
    user = User.objects.get(id=user_id)
    send_email(
        subject="Обновление статуса заказа",
        message="Заказ сформирован",
        recipient_email=user.email
    )


@shared_task(bind=True)
def load_data_from_url(self, url, user_id, task_id):
    task_status = TaskStatus.objects.get(task_id=task_id)
    task_status.status = 'IN_PROGRESS'
    task_status.save(update_fields=['status'])

    validate_url = URLValidator()
    try:
        validate_url(url)
        stream = get(url).content
        data = yaml.load(stream, Loader=yaml.Loader)

        shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=user_id)

        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(shop.id)
            category_object.save()

        ProductInfo.objects.filter(shop_id=shop.id).delete()
        for item in data['goods']:
            product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
            product_info = ProductInfo.objects.create(
                product_id=product.id,
                external_id=item['id'],
                model=item['model'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
                shop_id=shop.id
            )

            for name, value in item['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_object.id,
                    value=value
                )

        task_status.status = 'SUCCESS'
    except Exception as e:
        task_status.status = 'FAILED'
        task_status.error_message = str(e)
    finally:
        task_status.save(update_fields=['status'])
    return {'Status': task_status.status}
