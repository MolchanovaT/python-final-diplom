from unittest.mock import patch, MagicMock

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


# class LoadDataFromUrlTaskTest(TestCase):
#
#     @patch('django.core.validators.URLValidator')
#     @patch('requests.get')
#     @patch('backend.models.TaskStatus')
#     def test_load_data_from_url_success(self, MockTaskStatus, mock_get, mock_url_validator):
#         # Мокаем валидатор URL
#         mock_url_validator.return_value = None
#
#         # Мокаем успешный ответ от requests.get
#         mock_get.return_value.status_code = 200
#         mock_get.return_value.content = b"""
#             shop: "My Shop"
#             categories:
#               - id: 1
#                 name: "Electronics"
#               - id: 2
#                 name: "Books"
#             goods:
#               - id: 1
#                 name: "Laptop"
#                 category: 1
#                 model: "Model X"
#                 price: 1000
#                 price_rrc: 1200
#                 quantity: 10
#                 parameters:
#                   color: "black"
#                   ram: "16GB"
#               - id: 2
#                 name: "Book"
#                 category: 2
#                 model: "Book Model"
#                 price: 20
#                 price_rrc: 30
#                 quantity: 100
#                 parameters:
#                   author: "Author Name"
#             """
#
#         # Мокаем TaskStatus
#         task_status_instance = MagicMock()
#         task_status_instance.status = 'IN_PROGRESS'
#         task_status_instance.save = MagicMock()  # Мокаем метод save
#
#         # Мокаем возврат TaskStatus
#         MockTaskStatus.objects.get.return_value = task_status_instance
#
#         # Создаём пользователя
#         user = User.objects.create(email="testuser@example.com")
#
#         # Параметры задачи
#         url = 'http://example.com/data.yaml'
#         user_id = user.id
#         task_id = 'task_12345'
#
#         # Вызов функции
#         result = load_data_from_url(url, user_id, task_id)
#
#         # Проверяем, что статус изменился на SUCCESS
#         task_status_instance.status = 'SUCCESS'  # Явное изменение статуса
#         self.assertEqual(task_status_instance.status, 'SUCCESS')  # Проверяем, что статус изменился на 'SUCCESS'
#         task_status_instance.save.assert_called_with(update_fields=['status'])  # Проверяем, что метод save был вызван
#
#         # Дополнительные проверки на создание объектов
#         shop = Shop.objects.get(name="My Shop", user_id=user.id)
#         category_1 = Category.objects.get(id=1, name="Electronics")
#         category_2 = Category.objects.get(id=2, name="Books")
#         product_1 = Product.objects.get(name="Laptop", category=category_1)
#         product_2 = Product.objects.get(name="Book", category=category_2)
#
#         product_info_1 = ProductInfo.objects.get(product=product_1, shop=shop)
#         product_info_2 = ProductInfo.objects.get(product=product_2, shop=shop)
#
#         # Проверяем параметры товара
#         parameter_1 = Parameter.objects.get(name="color")
#         parameter_2 = Parameter.objects.get(name="ram")
#         parameter_3 = Parameter.objects.get(name="author")
#
#         product_parameter_1 = ProductParameter.objects.get(product_info=product_info_1, parameter=parameter_1)
#         product_parameter_2 = ProductParameter.objects.get(product_info=product_info_1, parameter=parameter_2)
#         product_parameter_3 = ProductParameter.objects.get(product_info=product_info_2, parameter=parameter_3)
#
#         # Проверяем, что товары и параметры были добавлены
#         self.assertEqual(product_parameter_1.value, "black")
#         self.assertEqual(product_parameter_2.value, "16GB")
#         self.assertEqual(product_parameter_3.value, "Author Name")
#
#     @patch('django.core.validators.URLValidator')
#     @patch('requests.get')
#     @patch('backend.models.TaskStatus')
#     def test_load_data_from_url_failure(self, MockTaskStatus, mock_get, mock_url_validator):
#         # Мокаем валидатор URL
#         mock_url_validator.return_value = None
#
#         # Мокаем ошибку при запросе
#         mock_get.return_value.status_code = 500  # Серверная ошибка
#
#         # Мокаем TaskStatus
#         task_status_instance = MagicMock()
#         task_status_instance.status = 'IN_PROGRESS'
#         task_status_instance.save = MagicMock()  # Мокаем метод save
#
#         # Мокаем возврат TaskStatus
#         MockTaskStatus.objects.get.return_value = task_status_instance
#
#         # Создаём пользователя
#         user = User.objects.create(email="testuser@example.com")
#
#         # Параметры задачи
#         url = 'http://example.com/data.yaml'
#         user_id = user.id
#         task_id = 'task_12345'
#
#         # Вызов функции
#         result = load_data_from_url(url, user_id, task_id)
#
#         # Проверяем, что статус изменился на FAILED
#         task_status_instance.status = 'FAILED'  # Явное изменение статуса на FAILED
#         self.assertEqual(task_status_instance.status, 'FAILED')  # Проверяем, что статус изменился на 'FAILED'
#         task_status_instance.save.assert_called_with(update_fields=['status'])  # Проверяем, что метод save был вызван


class TestLoadDataFromUrl(TestCase):
    @patch('backend.models.TaskStatus.objects.get')
    @patch('django.core.validators.URLValidator')
    @patch('requests.get')
    @patch('yaml.load')
    def test_load_data_from_url_success(self, mock_yaml_load, mock_get, mock_url_validator, mock_task_status_get):
        # Mock task status
        task_status = MagicMock()
        task_status.status = 'IN_PROGRESS'
        mock_task_status_get.return_value = task_status

        # Mock URL validation
        mock_url_validator.return_value = None

        # Mock HTTP request
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'yaml_data'
        mock_get.return_value = mock_response

        # Mock YAML loading
        mock_yaml_load.return_value = {
            'shop': 'shop_name',
            'categories': [{'id': 1, 'name': 'category_name'}],
            'goods': [{'id': 1, 'name': 'product_name', 'category': 1, 'model': 'model', 'price': 10, 'price_rrc': 5,
                       'quantity': 10, 'parameters': {'param1': 'value1'}}]
        }

        # Call the function
        print("Calling load_data_from_url")
        result = load_data_from_url('url', 'user_id', 'task_id')
        print(f"Result after calling the function: {result}")

        # Assert the result
        self.assertEqual(result, {'Status': 'SUCCESS'})  # Ожидаем результат 'SUCCESS'

        # Assert the task status updates
        print(f"Task status after execution: {task_status.status}")
        task_status.save.assert_called_with(
            update_fields=['status'])  # Проверяем, что save был вызван с правильным аргументом
        self.assertEqual(task_status.status, 'SUCCESS')  # Убедитесь, что статус был обновлен на 'SUCCESS'

    @patch('backend.models.TaskStatus.objects.get')
    def test_load_data_from_url_task_status_not_found(self, mock_task_status_get):
        # Mock task status not found
        mock_task_status_get.side_effect = TaskStatus.DoesNotExist

        # Call the function
        result = load_data_from_url('url', 'user_id', 'task_id')

        # Assert the result
        self.assertEqual(result, {'Status': 'FAILED', 'Error': 'TaskStatus not found'})

    @patch('backend.models.TaskStatus.objects.get')
    @patch('django.core.validators.URLValidator')
    @patch('requests.get')
    def test_load_data_from_url_exception(self, mock_get, mock_url_validator, mock_task_status_get):
        # Mock task status
        task_status = MagicMock()
        task_status.status = 'IN_PROGRESS'
        mock_task_status_get.return_value = task_status

        # Mock URL validation
        mock_url_validator.return_value = None

        # Mock HTTP request
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.side_effect = Exception('Mocked exception')

        # Call the function
        result = load_data_from_url('url', 'user_id', 'task_id')

        # Assert the result
        self.assertEqual(result, {'Status': 'FAILED'})

        # Assert the task status updates
        self.assertEqual(task_status.status, 'FAILED')
        task_status.save.assert_called_with(update_fields=['status', 'error_message'])
