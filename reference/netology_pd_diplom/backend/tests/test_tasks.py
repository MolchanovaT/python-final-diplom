from django.test import TestCase
from unittest.mock import patch, MagicMock
from backend.tasks import (
    send_email, send_password_reset_token, send_registration_confirmation,
    send_new_order_notification, load_data_from_url
)
from backend.models import User, ConfirmEmailToken, TaskStatus, Shop, Category, Product, ProductInfo, Parameter, \
    ProductParameter
from django.core.mail import EmailMultiAlternatives


class EmailTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="testuser@example.com")
        self.token = ConfirmEmailToken.objects.create(user=self.user)

    @patch.object(EmailMultiAlternatives, 'send', return_value=1)
    def test_send_email(self, mock_send):
        result = send_email("Test Subject", "Test Message", "testuser@example.com")
        self.assertTrue(mock_send.called)

    @patch('backend.tasks.send_email')
    def test_send_password_reset_token(self, mock_send_email):
        send_password_reset_token(self.token)
        mock_send_email.assert_called_once_with(
            subject=f"Password Reset Token for {self.token.user}",
            message=self.token.key,
            recipient_email=self.token.user.email
        )

    @patch('backend.tasks.send_email')
    def test_send_registration_confirmation(self, mock_send_email):
        send_registration_confirmation(self.user)
        token = ConfirmEmailToken.objects.get(user=self.user)
        mock_send_email.assert_called_once_with(
            subject=f"Password Reset Token for {self.user.email}",
            message=token.key,
            recipient_email=self.user.email
        )

    @patch('backend.tasks.send_email')
    def test_send_new_order_notification(self, mock_send_email):
        send_new_order_notification(self.user.id)
        mock_send_email.assert_called_once_with(
            subject="Обновление статуса заказа",
            message="Заказ сформирован",
            recipient_email=self.user.email
        )


class LoadDataFromURLTaskTests(TestCase):
    @patch('backend.tasks.get')
    @patch('backend.tasks.yaml.load', return_value={
        'shop': 'Test Shop',
        'categories': [{'id': 1, 'name': 'Category 1'}],
        'goods': [{
            'id': 1, 'name': 'Product 1', 'category': 1, 'model': 'Model 1',
            'price': 100, 'price_rrc': 120, 'quantity': 10,
            'parameters': {'Param 1': 'Value 1'}
        }]
    })
    def test_load_data_from_url_success(self, mock_yaml_load, mock_get):
        task_status = TaskStatus.objects.create(task_id='123', status='PENDING')
        user = User.objects.create(email="shopuser@example.com")

        # Вызов задачи и проверка статуса выполнения
        load_data_from_url("http://example.com/data.yaml", user.id, task_status.task_id)

        task_status.refresh_from_db()
        self.assertEqual(task_status.status, 'SUCCESS')

        # Проверка, что магазин, категории, продукты и параметры были созданы
        self.assertTrue(Shop.objects.filter(name="Test Shop").exists())
        self.assertTrue(Category.objects.filter(id=1, name="Category 1").exists())
        self.assertTrue(Product.objects.filter(name="Product 1").exists())
        self.assertTrue(Parameter.objects.filter(name="Param 1").exists())
        self.assertTrue(ProductParameter.objects.filter(value="Value 1").exists())

    @patch('backend.tasks.get')
    @patch('backend.tasks.yaml.load', side_effect=Exception("Error loading data"))
    def test_load_data_from_url_failure(self, mock_yaml_load, mock_get):
        task_status = TaskStatus.objects.create(task_id='123', status='PENDING')
        user = User.objects.create(email="shopuser@example.com")

        # Вызов задачи и проверка статуса выполнения
        load_data_from_url("http://example.com/data.yaml", user.id, task_status.task_id)

        task_status.refresh_from_db()
        self.assertEqual(task_status.status, 'FAILED')
        self.assertIn("Error loading data", task_status.error_message)
