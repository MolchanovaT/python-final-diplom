from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from celery import shared_task
from django.core.validators import URLValidator
from requests import get
import requests
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
def load_data_from_url(self, url, user_id):
    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        return {"Status": "FAILED", "Error": "User not found"}

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = yaml.safe_load(response.content)
    except requests.RequestException as e:
        return {"Status": "FAILED", "Error": f"Invalid URL or network error: {str(e)}"}
    except yaml.YAMLError as e:
        return {"Status": "FAILED", "Error": f"YAML parsing error: {str(e)}"}

    try:
        shop_data = data.get("shop")
        shop = Shop.objects.create(name=shop_data["name"], user=user)

        for category_data in data.get("categories", []):
            category = Category.objects.create(name=category_data["name"])
            category.shops.add(shop)

        for product_data in data.get("products", []):
            category = Category.objects.get(id=product_data["category"])
            product = Product.objects.create(name=product_data["name"], category=category)

            # Проверка наличия external_id
            external_id = product_data.get("external_id", None)
            if not external_id:
                return {"Status": "FAILED", "Error": f"Missing external_id for product {product_data['name']}"}

            # Создаем ProductInfo с учетом внешнего ID
            product_info = ProductInfo.objects.create(
                product=product,
                shop=shop,
                model=product_data["model"],
                price=product_data["price"],
                price_rrc=product_data.get("price_rrc", product_data["price"]),
                external_id=external_id,
                quantity=product_data.get("quantity", 0),  # Если количество не указано, ставим 0
            )

            for param_name, param_value in product_data.get("parameters", {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.create(
                    product_info=product_info, parameter=parameter, value=param_value
                )

        TaskStatus.objects.create(task_id=self.request.id, user=user, status="SUCCESS")
        return {"Status": "SUCCESS"}
    except Exception as e:
        return {"Status": "FAILED", "Error": f"Processing error: {str(e)}"}
