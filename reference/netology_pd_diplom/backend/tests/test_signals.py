from unittest.mock import patch, MagicMock

from backend.models import User
from backend.signals import new_order
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase
from django_rest_passwordreset.signals import reset_password_token_created

User = get_user_model()


class SignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="testuser@example.com", is_active=False)

    @patch('backend.tasks.send_password_reset_token.delay')
    def test_password_reset_token_created_signal(self, mock_send_task):
        """
        Тестирует, что задача send_password_reset_token вызывается при создании токена сброса пароля.
        """
        reset_password_token = MagicMock(key='dummy_token')

        # Срабатывание сигнала для создания токена сброса пароля
        reset_password_token_created.send(sender=None, instance=None, reset_password_token=reset_password_token)

        mock_send_task.assert_called_once_with(reset_password_token)

    @patch('backend.tasks.send_registration_confirmation.delay')
    def test_new_user_registered_signal(self, mock_send_task):
        """
        Тестирует, что задача send_registration_confirmation вызывается при создании нового неактивного пользователя.
        """
        # Срабатывание сигнала post_save для нового пользователя
        post_save.send(sender=User, instance=self.user, created=True)

        mock_send_task.assert_called_once_with(self.user)

    @patch('backend.tasks.send_new_order_notification.delay')
    def test_new_order_signal(self, mock_send_task):
        """
        Тестирует, что задача send_new_order_notification вызывается при срабатывании сигнала new_order.
        """
        user_id = self.user.id

        # Срабатывание сигнала new_order
        new_order.send(sender=None, user_id=user_id)

        mock_send_task.assert_called_once_with(user_id)
