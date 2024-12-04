from unittest.mock import patch, MagicMock

import requests
import yaml
from backend.models import User, ConfirmEmailToken, TaskStatus, Shop, Category, Product, Parameter, \
    ProductParameter, ProductInfo
from backend.tasks import (
    send_email, send_password_reset_token, send_registration_confirmation,
    send_new_order_notification, load_data_from_url
)
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase


class EmailTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="testuser@example.com")
        self.token = ConfirmEmailToken.objects.create(user=self.user)

    @patch.object(EmailMultiAlternatives, 'send', return_value=1)
    def test_send_email(self, mock_send):
        send_email("Test Subject", "Test Message", "testuser@example.com")
        self.assertTrue(mock_send.called)

    @patch('backend.tasks.send_email')
    def test_send_password_reset_token(self, mock_send_email):
        send_password_reset_token(self.token)
        mock_send_email.assert_called_once_with(
            subject=f"Password Reset Token for {self.token.user}",
            message=self.token.key,
            recipient_email=self.token.user.email
        )

    @patch("backend.tasks.send_email")  # Мокаем функцию отправки email
    @patch("backend.tasks.User.objects.get")  # Мокаем метод User.objects.get
    def test_send_registration_confirmation(self, mock_user_get, mock_send_email):
        # Настраиваем mock для User.objects.get
        mock_user_get.return_value = self.user

        # Вызываем задачу с user_id
        send_registration_confirmation(self.user.id)

        # Проверяем, что User.objects.get был вызван с правильным аргументом
        mock_user_get.assert_called_once_with(id=self.user.id)

        # Проверяем, что send_email был вызван с правильными именованными аргументами
        mock_send_email.assert_called_once_with(
            subject="Подтверждение регистрации",  # Тема письма
            message=f"Confirmation code for {self.user.email}: {self.token.key}",  # Текст письма с токеном
            recipient_list=[self.user.email],  # Адрес электронной почты в виде списка
        )

    @patch('backend.tasks.send_email')
    def test_send_new_order_notification(self, mock_send_email):
        send_new_order_notification(self.user.id)
        mock_send_email.assert_called_once_with(
            subject="Обновление статуса заказа",
            message="Заказ сформирован",
            recipient_email=self.user.email
        )


class TestLoadDataFromUrlTask(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="password"
        )
        self.valid_url = "http://example.com/valid.yaml"
        self.invalid_url = "http://example.com/invalid.yaml"
        self.sample_yaml_data = {
            "shop": {"name": "Test Shop"},
            "categories": [{"name": "Category 1"}],
            "products": [
                {
                    "name": "Product 1",
                    "category": 1,
                    "model": "Model 1",
                    "price": 100.0,
                    "parameters": {"Color": "Red"},
                    "external_id": 123,
                }
            ],
        }

    @patch("backend.tasks.requests.get")
    @patch("backend.tasks.yaml.safe_load")
    def test_load_data_from_url_success(self, mock_yaml_load, mock_get):
        mock_get.return_value.content = "mocked content"
        mock_get.return_value.raise_for_status = MagicMock()
        mock_yaml_load.return_value = self.sample_yaml_data  # Обновленные данные

        # Запускаем задачу
        result = load_data_from_url.apply(args=[self.valid_url, self.user.id]).result

        # Проверяем результат
        self.assertEqual(result["Status"], "SUCCESS")

        # Проверяем создание объектов в базе
        shop = Shop.objects.get(name="Test Shop")
        self.assertEqual(shop.user, self.user)

        category = Category.objects.get(name="Category 1")
        self.assertIn(shop, category.shops.all())

        product = Product.objects.get(name="Product 1")
        self.assertEqual(product.category, category)

        product_info = ProductInfo.objects.get(product=product)
        self.assertEqual(product_info.model, "Model 1")
        self.assertEqual(product_info.price, 100.0)
        self.assertEqual(product_info.external_id, 123)  # Проверяем external_id
        self.assertEqual(product_info.quantity, 0)  # Проверяем количество по умолчанию

        parameter = Parameter.objects.get(name="Color")
        product_parameter = ProductParameter.objects.get(product_info=product_info, parameter=parameter)
        self.assertEqual(product_parameter.value, "Red")

    def test_load_data_from_url_user_not_found(self):
        result = load_data_from_url.apply(args=[self.valid_url, 999]).result
        self.assertEqual(result["Status"], "FAILED")
        self.assertEqual(result["Error"], "User not found")

    @patch("backend.tasks.requests.get")
    def test_load_data_from_url_invalid_url(self, mock_get):
        mock_get.side_effect = requests.RequestException("Invalid URL")
        result = load_data_from_url.apply(args=[self.invalid_url, self.user.id]).result
        self.assertEqual(result["Status"], "FAILED")
        self.assertIn("Invalid URL", result["Error"])

    @patch("backend.tasks.requests.get")
    @patch("backend.tasks.yaml.safe_load")
    def test_load_data_from_url_yaml_error(self, mock_yaml_load, mock_get):
        mock_get.return_value.content = "mocked content"
        mock_get.return_value.raise_for_status = MagicMock()
        mock_yaml_load.side_effect = yaml.YAMLError("YAML Error")

        result = load_data_from_url.apply(args=[self.valid_url, self.user.id]).result
        self.assertEqual(result["Status"], "FAILED")
        self.assertIn("YAML parsing error", result["Error"])
