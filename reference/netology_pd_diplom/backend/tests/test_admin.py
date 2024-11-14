from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse
from unittest.mock import patch
from backend.admin import start_load_data_task, TaskStatusAdmin, ShopAdmin
from backend.models import TaskStatus, Shop
from backend.forms import LoadDataForm

User = get_user_model()


class TaskStatusAdminTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="admin@example.com", password="admin")
        self.client.force_login(self.user)
        self.factory = RequestFactory()

    def test_task_status_admin_display_fields(self):
        """
        Тестирование отображения полей в TaskStatusAdmin.
        """
        task_status = TaskStatus.objects.create(task_id="123", user=self.user, status="PENDING")
        url = reverse('admin:backend_taskstatus_changelist')
        response = self.client.get(url)
        self.assertContains(response, task_status.task_id)
        self.assertContains(response, task_status.status)

    def test_task_status_admin_readonly_fields(self):
        """
        Тестирование, что поля `readonly_fields` отображаются только для чтения.
        """
        task_status = TaskStatus.objects.create(task_id="123", user=self.user, status="PENDING")
        url = reverse('admin:backend_taskstatus_change', args=[task_status.pk])
        response = self.client.get(url)
        self.assertContains(response, 'readonly')


class ShopAdminTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="admin@example.com", password="admin")
        self.client.force_login(self.user)
        self.factory = RequestFactory()
        self.shop = Shop.objects.create(name="Test Shop", user=self.user)

    @patch("backend.admin.load_data_from_url.apply_async")
    def test_start_load_data_task_action_with_valid_url(self, mock_apply_async):
        """
        Тестирование действия `start_load_data_task` при корректном URL.
        """
        url = reverse('admin:backend_shop_changelist')
        form_data = {'url': 'https://example.com/data.yaml', 'apply': '1'}
        request = self.factory.post(url, data=form_data)
        request.user = self.user

        form = LoadDataForm(form_data)
        self.assertTrue(form.is_valid())

        response = start_load_data_task(ShopAdmin(Shop, admin.site), request, [self.shop])

        # Проверяем, что сообщение отправлено
        self.assertIsNone(response)
        self.assertTrue(mock_apply_async.called)
        self.assertEqual(TaskStatus.objects.count(), 1)
        task_status = TaskStatus.objects.first()
        self.assertEqual(task_status.status, 'PENDING')
        self.assertEqual(task_status.user, self.user)

    def test_start_load_data_task_action_invalid_url(self):
        """
        Тестирование действия `start_load_data_task` с некорректным URL.
        """
        url = reverse('admin:backend_shop_changelist')
        form_data = {'url': 'invalid-url', 'apply': '1'}
        request = self.factory.post(url, data=form_data)
        request.user = self.user

        form = LoadDataForm(form_data)
        self.assertFalse(form.is_valid())

        response = start_load_data_task(ShopAdmin(Shop, admin.site), request, [self.shop])

        # Проверяем, что форма отображена снова с ошибкой
        self.assertContains(response, 'Enter a valid URL')
