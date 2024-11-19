from unittest.mock import patch, MagicMock

import yaml
from backend.models import User, ConfirmEmailToken, TaskStatus, Shop, Category, Product, Parameter, \
    ProductParameter
from backend.tasks import (
    send_email, send_password_reset_token, send_registration_confirmation,
    send_new_order_notification, load_data_from_url
)
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase

from reference.netology_pd_diplom.backend.models import ProductInfo


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


class LoadDataFromUrlTaskTest(TestCase):

    @patch('django.core.validators.URLValidator')
    @patch('requests.get')  # Мокаем запрос
    @patch('your_app.models.TaskStatus')  # Мокаем модель TaskStatus
    def test_load_data_from_url_success(self, MockTaskStatus, mock_get, mock_url_validator):
        # Мокаем URLValidator
        mock_url_validator.return_value = None  # Допускаем, что URL проходит валидацию без ошибок

        # Мокаем получение данных с URL
        mock_response = MagicMock()
        mock_response.content = yaml.dump({
            'shop': 'Test Shop',
            'categories': [
                {'id': 1, 'name': 'Category 1'},
                {'id': 2, 'name': 'Category 2'},
            ],
            'goods': [
                {'id': 101, 'name': 'Product 1', 'category': 1, 'model': 'Model 1', 'price': 100, 'price_rrc': 120,
                 'quantity': 10, 'parameters': {'color': 'black'}},
                {'id': 102, 'name': 'Product 2', 'category': 2, 'model': 'Model 2', 'price': 150, 'price_rrc': 170,
                 'quantity': 5, 'parameters': {'color': 'white'}}
            ]
        })
        mock_get.return_value = mock_response

        # Мокаем создание и обновление TaskStatus
        mock_task_status = MagicMock(spec=TaskStatus)
        mock_task_status.status = 'IN_PROGRESS'
        mock_task_status.save = MagicMock()
        MockTaskStatus.objects.get.return_value = mock_task_status

        # Создаем пользователя
        user = User.objects.create(email="testuser@example.com")

        # Запуск задачи
        url = 'http://example.com/data.yaml'
        user_id = user.id  # Используем ID пользователя, а не сам объект
        task_id = 'task_12345'

        result = load_data_from_url(url, user_id, task_id)

        # Проверка изменений в статусе задачи
        mock_task_status.save.assert_called_with(update_fields=['status'])
        self.assertEqual(result['Status'], 'SUCCESS')

        # Проверка, что объекты были созданы
        self.assertEqual(Shop.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 2)
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(ProductInfo.objects.count(), 2)
        self.assertEqual(ProductParameter.objects.count(), 2)

    @patch('django.core.validators.URLValidator')
    @patch('requests.get')  # Мокаем запрос
    @patch('your_app.models.TaskStatus')  # Мокаем модель TaskStatus
    def test_load_data_from_url_failure(self, MockTaskStatus, mock_get, mock_url_validator):
        # Мокаем URLValidator
        mock_url_validator.return_value = None  # Допускаем, что URL проходит валидацию без ошибок

        # Мокаем ошибку при получении данных
        mock_get.side_effect = Exception("Network error")

        # Мокаем создание и обновление TaskStatus
        mock_task_status = MagicMock(spec=TaskStatus)
        mock_task_status.status = 'IN_PROGRESS'
        mock_task_status.save = MagicMock()
        MockTaskStatus.objects.get.return_value = mock_task_status

        # Создаем пользователя
        user = User.objects.create(email="testuser@example.com")

        # Запуск задачи
        url = 'http://example.com/data.yaml'
        user_id = user.id  # Используем ID пользователя
        task_id = 'task_12345'

        result = load_data_from_url(url, user_id, task_id)

        # Проверка, что статус изменился на 'FAILED'
        mock_task_status.save.assert_called_with(update_fields=['status'])
        self.assertEqual(result['Status'], 'FAILED')

        # Проверка, что объекты не были созданы
        self.assertEqual(Shop.objects.count(), 0)
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(ProductInfo.objects.count(), 0)
        self.assertEqual(ProductParameter.objects.count(), 0)
