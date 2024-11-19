from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from backend.models import Shop, TaskStatus
from unittest.mock import patch

User = get_user_model()


class TestShopAdmin(TestCase):
    def setUp(self):
        # Создаем суперпользователя
        self.user = User.objects.create_superuser(
            email="admin@example.com",
            password="password123"
        )

        # Создаем тестовый магазин
        self.shop = Shop.objects.create(
            name="Test Shop",
            user=self.user,
            url="https://example.com/data.yaml"
        )

        # Логинимся как суперпользователь
        logged_in = self.client.login(email="admin@example.com", password="password123")
        self.assertTrue(logged_in)  # Убеждаемся, что логин успешен

    @patch("backend.admin.load_data_from_url.apply_async")  # Мокаем задачу Celery
    def test_start_load_data_task(self, mock_apply_async):
        """
        Проверяем, что действие start_load_data_task работает корректно.
        """
        # Настраиваем мок для Celery задачи
        mock_apply_async.return_value.id = "mocked-task-id"

        # Отправляем POST-запрос для выполнения действия
        response = self.client.post(
            reverse('admin:backend_shop_changelist'),
            {
                'action': 'start_load_data_task',
                '_selected_action': [self.shop.pk],
                'apply': True,
                'url': self.shop.url
            }
        )

        # Проверяем редирект
        self.assertRedirects(response, reverse('admin:backend_shop_changelist'))

        # Проверяем, что TaskStatus создан
        task_status = TaskStatus.objects.last()
        self.assertIsNotNone(task_status)
        self.assertEqual(task_status.user, self.user)
        self.assertEqual(task_status.task_id, "mocked-task-id")
        self.assertEqual(task_status.status, "PENDING")

        # Проверяем, что задача Celery вызвана с правильными аргументами
        mock_apply_async.assert_called_once_with(args=[self.shop.url, self.shop.user_id])

    @patch("backend.admin.load_data_from_url.apply_async")  # Мокаем задачу Celery
    def test_start_load_data_task_message(self, mock_apply_async):
        """
        Проверяем, что после выполнения действия появляется сообщение.
        """
        # Настраиваем мок для Celery задачи
        mock_apply_async.return_value.id = "mocked-task-id"

        # Отправляем POST-запрос для выполнения действия
        response = self.client.post(
            reverse('admin:backend_shop_changelist'),
            {
                'action': 'start_load_data_task',
                '_selected_action': [self.shop.pk],
                'apply': True,
                'url': self.shop.url
            },
            follow=True  # Для обработки редиректа и получения сообщений
        )

        # Проверяем, что сообщение добавлено
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Задача загружена в очередь")
