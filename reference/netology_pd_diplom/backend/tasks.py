from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from celery import shared_task
from django.core.validators import URLValidator
from requests import get
import yaml
from backend.models import Shop, Category, ProductInfo, Product, Parameter, ProductParameter, TaskStatus, \
    ConfirmEmailToken, User


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
def send_registration_confirmation(user_id):
    try:
        user = User.objects.get(id=user_id)
        token, created = ConfirmEmailToken.objects.get_or_create(user=user)  # Генерация или получение токена
        # Логика отправки письма пользователю
        send_email(
            subject="Подтверждение регистрации",
            recipient_list=[user.email],
            message=f'Confirmation code for {user.email}: {token.key}',
        )
        print(f"Отправка подтверждения регистрации для пользователя: {user.email}")
    except User.DoesNotExist:
        print(f"Пользователь с id {user_id} не найден.")


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
    task_status = None
    try:
        print("Starting task...")
        task_status = TaskStatus.objects.get(task_id=task_id)
        print(f"Initial status: {task_status.status}")  # Логирование начального статуса
        task_status.status = 'IN_PROGRESS'
        task_status.save(update_fields=['status'])

        # Проверяем валидность URL
        validate_url = URLValidator()
        validate_url(url)

        # Загружаем данные из URL
        response = get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP
        data = yaml.load(response.content, Loader=yaml.Loader)

        # Создаём магазин
        shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=user_id)

        # Добавляем категории
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(shop.id)
            category_object.save()

        # Удаляем старую информацию о товарах
        ProductInfo.objects.filter(shop_id=shop.id).delete()

        # Добавляем товары
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

            # Добавляем параметры товара
            for name, value in item['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_object.id,
                    value=value
                )

        print(f"Before successful status update: {task_status.status}")
        # Успешное завершение задачи
        if task_status:
            task_status.status = 'SUCCESS'
            task_status.save(update_fields=['status'])
        print(f"Task status after success: {task_status.status}")

    except TaskStatus.DoesNotExist:
        # Если задача не найдена, возвращаем ошибку
        return {'Status': 'FAILED', 'Error': 'TaskStatus not found'}

    except Exception as e:
        # Обновляем статус на "FAILED" при возникновении ошибки
        if task_status:
            task_status.status = 'FAILED'
            task_status.error_message = str(e)
            task_status.save(update_fields=['status', 'error_message'])

    finally:
        # Гарантируем сохранение статуса в любом случае
        if task_status:
            print(f"Final status in finally block: {task_status.status}")  # Логируем финальный статус
            task_status.save(update_fields=['status', 'error_message'])

    # Возвращаем статус задачи
    return {'Status': task_status.status}
