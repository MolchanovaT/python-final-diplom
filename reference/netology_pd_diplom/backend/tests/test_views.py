import json
from unittest.mock import patch, MagicMock

from backend.forms import LoadDataForm
from backend.models import Category, ProductParameter, Product
from backend.models import ConfirmEmailToken
from backend.models import Contact
from backend.models import Order
from backend.models import OrderItem, ProductInfo, Shop
from backend.models import TaskStatus
from backend.serializers import ContactSerializer
from backend.serializers import ShopSerializer
from backend.views import AccountDetails
from backend.views import ConfirmAccount
from backend.views import LoginAccount
from backend.views import OrderView
from backend.views import PartnerOrders
from backend.views import RegisterAccount
from backend.views import ShopView
from backend.views import BasketView
from backend.views import run_task_view
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase, force_authenticate

import uuid

User = get_user_model()


class TestRunTaskView(TestCase):
    def setUp(self):
        # Создаем фабрику запросов и тестового пользователя
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def add_middleware(self, request):
        """Добавляем сессии и сообщения к запросу."""
        # Сессии
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()

        # Сообщения
        message_middleware = MessageMiddleware(lambda req: None)
        message_middleware.process_request(request)
        return request

    def test_run_task_view_get(self):
        """Тестируем GET-запрос: отображение формы."""
        request = self.factory.get(reverse("run-task"))  # Замените на правильный URL
        request.user = self.user
        request = self.add_middleware(request)

        response = run_task_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")  # Проверяем, что форма отобразилась

    @patch("backend.views.load_data_from_url.apply_async")
    def test_run_task_view_post_valid_form(self, mock_apply_async):
        """Тестируем POST-запрос с валидной формой."""
        mock_apply_async.return_value.id = "test-task-id"  # Мокаем Celery задачу

        data = {"url": "http://example.com/test.yaml"}  # Данные для формы
        request = self.factory.post(reverse("run-task"), data)
        request.user = self.user
        request = self.add_middleware(request)

        response = run_task_view(request)
        self.assertEqual(response.status_code, 302)  # Должен быть редирект
        self.assertEqual(response.url, "/admin/backend/shop/")  # Проверяем URL редиректа

        # Проверяем, что задача была добавлена
        mock_apply_async.assert_called_once_with(args=["http://example.com/test.yaml"])

        # Проверяем, что TaskStatus создан
        task_status = TaskStatus.objects.get(user=self.user, task_id="test-task-id")
        self.assertEqual(task_status.status, "PENDING")

    def test_run_task_view_post_invalid_form(self):
        """Тестируем POST-запрос с невалидной формой."""
        data = {"url": ""}  # Некорректные данные
        request = self.factory.post(reverse("run-task"), data)
        request.user = self.user
        request = self.add_middleware(request)

        response = run_task_view(request)
        self.assertEqual(response.status_code, 200)  # Страница должна перезагрузиться
        self.assertContains(response, "form")  # Форма должна остаться на странице
        self.assertFalse(TaskStatus.objects.filter(user=self.user).exists())  # TaskStatus не должен быть создан


class TestRegisterAccount(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_register_account_post_valid_data(self):
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'P@ssw0rd123!',  # Убедитесь, что пароль соответствует требованиям
            'company': 'Test Company',
            'position': 'Test Position'
        }
        request = self.factory.post('/register', data=json.dumps(data), content_type='application/json')
        response = RegisterAccount.as_view()(request)
        response_data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['Status'], True)

    def test_register_account_post_invalid_password(self):
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'password',
            'company': 'Test Company',
            'position': 'Test Position'
        }
        request = self.factory.post('/register', data=data, content_type='application/json')
        response = RegisterAccount.as_view()(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['Status'], False)
        self.assertIn('password', response_data['Errors'])

    def test_register_account_post_missing_fields(self):
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'P@ssw0rd',
            'company': 'Test Company'
        }
        request = self.factory.post('/register', data=data, content_type='application/json')
        response = RegisterAccount.as_view()(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не указаны все необходимые аргументы')

    def test_register_account_post_invalid_serializer_data(self):
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'invalid_email',  # Неверный email
            'password': 'P@ssw0rd123!',  # Валидный пароль
            'company': 'Test Company',
            'position': 'Test Position'
        }
        request = self.factory.post('/register', data=json.dumps(data), content_type='application/json')
        response = RegisterAccount.as_view()(request)
        response_data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['Status'], False)
        self.assertIn('email', response_data['Errors'])  # Убедимся, что ошибка связана с email


class TestConfirmAccount(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.token = ConfirmEmailToken.objects.create(
            user=self.user,
            key='testkey'
        )

    def test_confirm_email_success(self):
        data = {'email': 'test@example.com', 'token': 'testkey'}
        request = self.factory.post('/confirm-account/', data=data)
        response = ConfirmAccount.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"Status": true}')
        self.assertTrue(User.objects.get(email='test@example.com').is_active)
        self.assertFalse(ConfirmEmailToken.objects.filter(user=self.user).exists())

    def test_confirm_email_failure_invalid_token(self):
        data = {'email': 'test@example.com', 'token': 'invalid'}
        request = self.factory.post('/confirm-account/', data=data)
        response = ConfirmAccount.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"Status": false, "Errors": "Wrong token or email"}')
        self.assertFalse(User.objects.get(email='test@example.com').is_active)
        self.assertTrue(ConfirmEmailToken.objects.filter(user=self.user).exists())

    def test_confirm_email_failure_missing_arguments(self):
        data = {'email': 'test@example.com'}
        request = self.factory.post('/confirm-account/', data=data)
        response = ConfirmAccount.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"Status": false, "Errors": "Not all required arguments specified"}')
        self.assertFalse(User.objects.get(email='test@example.com').is_active)
        self.assertTrue(ConfirmEmailToken.objects.filter(user=self.user).exists())

    class TestAccountDetails(APITestCase):
        def setUp(self):
            self.factory = RequestFactory()
            self.user = User.objects.create_user(
                username='testuser',
                email='testuser@example.com',
                password='testpassword'
            )

        def test_get_account_details_unauthenticated(self):
            request = self.factory.get('/account-details/')
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        def test_get_account_details_authenticated(self):
            request = self.factory.get('/account-details/')
            force_authenticate(request, user=self.user)
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_post_account_details_unauthenticated(self):
            request = self.factory.post('/account-details/', {})
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        def test_post_account_details_password_update(self):
            request = self.factory.post('/account-details/', {'password': 'newpassword'})
            request.user = self.user
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_post_account_details_password_update_invalid(self):
            request = self.factory.post('/account-details/', {'password': 'short'})
            request.user = self.user
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('password', response.data['Errors'])

        def test_post_account_details_user_update(self):
            request = self.factory.post('/account-details/', {'email': 'newemail@example.com'})
            request.user = self.user
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_post_account_details_user_update_invalid(self):
            request = self.factory.post('/account-details/', {'email': 'invalid'})
            request.user = self.user
            response = AccountDetails.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('email', response.data['Errors'])

    class TestPasswordValidation(TestCase):
        def test_password_validation(self):
            with self.assertRaises(ValidationError):
                validate_password('short')

        def test_password_validation_valid(self):
            try:
                validate_password('longpassword123')
            except ValidationError:
                self.fail("Password validation failed unexpectedly")


class TestLoginAccount(APITestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='password123',
            is_active=True  # Указываем явно, что пользователь активен
        )

    def test_login_account_post_valid_credentials(self):
        data = {'email': 'testuser@example.com', 'password': 'password123'}
        request = self.factory.post(
            reverse('user-login'),
            data=json.dumps(data),  # Преобразуем данные в JSON
            content_type='application/json'
        )
        response = LoginAccount.as_view()(request)

        # Парсим JSON-ответ
        response_data = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data['Status'], True)

    def test_login_account_post_invalid_credentials(self):
        data = {'email': 'testuser@example.com', 'password': 'wrongpassword'}
        request = self.factory.post(
            reverse('user-login'),
            data=json.dumps(data),  # Преобразуем данные в JSON
            content_type='application/json'
        )
        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = json.loads(response.content)
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не удалось авторизовать')

    def test_login_account_post_missing_credentials(self):
        data = {'email': 'testuser@example.com'}
        request = self.factory.post(reverse('user-login'), data=data, content_type='application/json')

        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = json.loads(response.content)
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не указаны все необходимые аргументы')

    def test_login_account_post_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        data = {'email': 'testuser@example.com', 'password': 'password123'}
        request = self.factory.post(reverse('user-login'), data=data, content_type='application/json')

        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = json.loads(response.content)
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не удалось авторизовать')


class ShopViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ShopView.as_view()

    def test_get_shops(self):
        # Создание тестового магазина
        test_shop = Shop.objects.create(name="Test Shop", state=True)

        # Создание запроса
        request = self.factory.get('/shops/')
        response = self.view(request)

        # Проверка статуса ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка данных
        expected_data = ShopSerializer(test_shop).data
        self.assertEqual(response.data['results'], [expected_data])

    def test_get_shops_empty(self):
        # Создание запроса
        request = self.factory.get('/shops/')
        response = self.view(request)

        # Проверка статуса ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка данных
        self.assertEqual(response.data['results'], [])


class ProductInfoViewTests(APITestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name='Test Shop', state=True)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product_info = ProductInfo.objects.create(
            shop=self.shop,
            product=self.product,
            quantity=10,
            price=100.00,
            price_rrc=120.00,
            external_id=1  # Указываем external_id
        )

    def test_get_product_info(self):
        url = reverse('products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_shop_id(self):
        url = reverse('products')
        response = self.client.get(url, {'shop_id': self.shop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_category_id(self):
        url = reverse('products')
        response = self.client.get(url, {'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_shop_id_and_category_id(self):
        url = reverse('products')
        response = self.client.get(url, {'shop_id': self.shop.id, 'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_invalid_shop_id(self):
        url = reverse('products')
        response = self.client.get(url, {'shop_id': 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_product_info_with_invalid_category_id(self):
        url = reverse('products')
        response = self.client.get(url, {'category_id': 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class BasketViewTests(APITestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = BasketView.as_view()
        # Создаём пользователя
        self.client = APIClient()
        self.user = self.create_user()
        self.client.force_authenticate(user=self.user)

        # Создаём категорию и магазин
        self.category = Category.objects.create(name='Test Category')
        self.shop = Shop.objects.create(name='Test Shop', state=True)

        # Создаём продукт
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product2 = Product.objects.create(name='Test Product2', category=self.category)

        # Создаём информацию о продукте с external_id
        self.product_info = ProductInfo.objects.create(
            shop=self.shop,
            product=self.product,
            quantity=10,
            price=100.00,
            price_rrc=120.00,
            external_id=1  # Указываем external_id
        )
        self.product_info2 = ProductInfo.objects.create(
            shop=self.shop,
            product=self.product2,
            quantity=20,
            price=200.00,
            price_rrc=220.00,
            external_id=2  # Указываем external_id
        )

        # Создаём заказ и элемент заказа
        self.basket, _ = Order.objects.get_or_create(user=self.user, state='basket')
        self.item1 = OrderItem.objects.create(order=self.basket,
                                              product_info=self.product_info,
                                              quantity=1)
        self.item2 = OrderItem.objects.create(order=self.basket,
                                              product_info=self.product_info2,
                                              quantity=1)

        self.url = reverse('basket')

    def create_user(self):
        user_data = {
            'username': 'test_user',
            'password': 'test_password',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'company': 'Test Company',
            'position': 'Test Position'
        }
        # Используем менеджер для создания пользователя напрямую
        user = User.objects.create_user(
            username=user_data['username'],
            password=user_data['password'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            company=user_data['company'],
            position=user_data['position']
        )
        return user

    def test_get_basket(self):
        response = self.client.get(reverse('basket'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_post_basket(self):
        data = {
            'items': json.dumps([{'product_info': self.product_info.id, 'quantity': 1}])
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.quantity, 2)
        self.assertEqual(response.json().get('Создано объектов'), 0)

    def test_post_basket_create_new_item(self):
        product3 = Product.objects.create(name='Test Product3', category=self.category)
        product_info_new = ProductInfo.objects.create(
            shop=self.shop,
            product=product3,
            quantity=15,
            price=150.00,
            price_rrc=170.00,
            external_id=3  # Новый external_id
        )
        data = {
            'items': json.dumps([{'product_info': product_info_new.id, 'quantity': 1}])
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json().get('Создано объектов'), 1)
        self.assertTrue(OrderItem.objects.filter(product_info_id=product_info_new.id).exists())

    def test_post_basket_invalid_data(self):
        data = {
            'items': json.dumps([{'invalid_field': 'Invalid Value'}])
        }
        response = self.client.post(reverse('basket'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_basket(self):
        """
        Test that items can be deleted from the user's basket.
        """
        data = {'items': f'{self.item1.id},{self.item2.id}'}
        response = self.client.delete(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('Удалено объектов', response_data)
        self.assertEqual(response_data['Удалено объектов'], 2)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_delete_basket_unauthenticated(self):
        """
        Test that the delete action returns a 403 error if the user is not authenticated.
        """
        self.client.logout()
        data = {'items': f'{self.item1.id},{self.item2.id}'}
        response = self.client.delete(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['Error'], 'Log in required')

    def test_delete_basket_invalid_items(self):
        """
        Test that the delete action returns an error if invalid items are provided.
        """
        data = {'items': 'invalid_id'}
        response = self.client.delete(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не указаны все необходимые аргументы')

    def test_delete_basket_empty(self):
        """
        Test that the delete action returns an error if no items are specified.
        """
        data = {'items': ''}
        response = self.client.delete(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не указаны все необходимые аргументы')

    def test_put_basket(self):
        """
        Test updating the basket with valid data.
        """
        # Передаём список с элементами и их количеством в формате JSON
        data = {
            'items': json.dumps([{'id': self.item1.id, 'quantity': 2}])  # Пример данных
        }

        # Отправляем PUT запрос
        response = self.client.put(self.url, data, format='json')

        # Проверяем статус ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Извлекаем данные из JsonResponse
        response_data = response.json()
        self.assertEqual(response_data['Обновлено объектов'], 1)

        # Проверяем изменения в базе данных
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.quantity, 2)


class TestPartnerUpdateView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword'
        )
        self.user.type = 'shop'
        self.user.save()

    def test_partner_update_view_post_unauthenticated(self):
        client = APIClient()
        response = client.post(reverse('partner-update'), {'url': 'http://example.com'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(json.loads(response.content), {'Status': False, 'Error': 'Log in required'})

    def test_partner_update_view_post_invalid_user_type(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        self.user.type = 'not_shop'
        self.user.save()
        response = client.post(reverse('partner-update'), {'url': 'http://example.com'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(json.loads(response.content), {'Status': False, 'Error': 'Только для магазинов'})

    def test_partner_update_view_post_valid_request(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(reverse('partner-update'), {'url': 'http://example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('TaskID', json.loads(response.content))

    def test_partner_update_view_post_missing_url(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(reverse('partner-update'), {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content),
                         {'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class TestPartnerState(APITestCase):

    def setUp(self):
        self.factory = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com', password='password123', type='shop')
        self.user.shop = Shop.objects.create(user=self.user)

    def test_partner_state_get_unauthenticated(self):
        response = self.factory.get(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Log in required'})

    def test_partner_state_get_not_shop(self):
        user = User.objects.create_user(email='testuser2@example.com', password='password123', type='not_shop')
        self.factory.force_authenticate(user=user)
        response = self.factory.get(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Только для магазинов'})

    def test_partner_state_get_authenticated(self):
        self.factory.force_authenticate(user=self.user)
        response = self.factory.get(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), dict)
        self.assertEqual(response.json(), ShopSerializer(self.user.shop).data)

    def test_partner_state_post_unauthenticated(self):
        response = self.factory.post(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Log in required'})

    def test_partner_state_post_not_shop(self):
        user = User.objects.create_user(email='testuser2@example.com', password='password123', type='not_shop')
        self.factory.force_authenticate(user=user)
        response = self.factory.post(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Только для магазинов'})

    def test_partner_state_post_authenticated_missing_state(self):
        self.factory.force_authenticate(user=self.user)
        response = self.factory.post(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def test_partner_state_post_authenticated_invalid_state(self):
        self.factory.force_authenticate(user=self.user)
        response = self.factory.post(reverse('partner-state'), data={'state': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'Status': False, 'Errors': "invalid truth value 'invalid'"})

    def test_partner_state_post_authenticated_valid_state(self):
        self.factory.force_authenticate(user=self.user)
        response = self.factory.post(reverse('partner-state'), data={'state': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'Status': True})


class PartnerOrdersTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PartnerOrders.as_view()

        # Создаем пользователя с типом 'shop'
        self.user = User.objects.create_user(
            email=f'{uuid.uuid4()}@example.com',
            password='password123',
            type='shop',
            is_active=True
        )

        # Создаем магазин, связывая его с пользователем
        self.shop = Shop.objects.create(name='Test Shop', state=True)
        self.shop.user = self.user
        self.shop.save()

        # Создаем категорию, продукт и заказ
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)

        self.order = Order.objects.create(user=self.user, state='new')

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product_info=ProductInfo.objects.create(
                shop=self.shop,
                product=self.product,
                quantity=10,
                price=100.00,
                price_rrc=120.00,
                external_id=1
            ),
            quantity=2  # Количество товаров в заказе
        )

    def test_get_unauthenticated(self):
        request = self.factory.get(reverse('partner-orders'))
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'Status': False, 'Error': 'Log in required'})

    def test_get_not_shop(self):
        not_shop_user = get_user_model().objects.create_user(
            email='testuser2@example.com',
            password='password123',
            type='not_shop',
            is_active=True
        )
        request = self.factory.get(reverse('partner-orders'))
        force_authenticate(request, user=not_shop_user)
        response = self.view(request)

        self.assertEqual(response.status_code, 403)

        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'Status': False, 'Error': 'Только для магазинов'})

    def test_get_valid(self):
        request = self.factory.get(reverse('partner-orders'))
        force_authenticate(request, user=self.user)
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        total_sum = self.order_item.quantity * self.order_item.product_info.price

        orders_data = [{
            'id': self.order.id,
            'user_id': self.user.id,
            'total_sum': total_sum,  # Ожидаемое значение как число
        }]

        self.assertEqual(response_data, orders_data)

    def test_get_invalid(self):
        # Создаем нового пользователя, у которого нет заказов
        invalid_user = User.objects.create_user(
            email=f'{uuid.uuid4()}@example.com',
            password='password123',
            type='shop',
            is_active=True
        )
        Shop.objects.create(name='Invalid Shop', user=invalid_user)

        # Аутентифицируем этого пользователя
        request = self.factory.get(reverse('partner-orders'))
        force_authenticate(request, user=invalid_user)
        response = self.view(request)

        # Ожидаем, что ответ вернет 404, так как заказов нет
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content),
            {'Status': False, 'Error': 'No orders found'}
        )


class TestContactView(APITestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='password123',
            is_active=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_contact(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        response = self.client.get(reverse('user-contact'))
        serializer = ContactSerializer(contact)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [serializer.data])

    def test_get_contact_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('user-contact'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_contact(self):
        data = {'city': 'city', 'street': 'street', 'phone': 'phone'}
        response = self.client.post(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.count(), 1)

    def test_post_contact_unauthenticated(self):
        self.client.logout()
        data = {'city': 'city', 'street': 'street', 'phone': 'phone'}
        response = self.client.post(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_contact_invalid_data(self):
        data = {'city': 'city', 'street': 'street'}
        response = self.client.post(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не указаны все необходимые аргументы')

    def test_delete_contact(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'items': str(contact.id)}
        response = self.client.delete(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.count(), 0)

    def test_delete_contact_unauthenticated(self):
        self.client.logout()
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'items': str(contact.id)}
        response = self.client.delete(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_contact_invalid_data(self):
        """
        Test that the delete action returns an error if invalid items are provided.
        """
        # Отправляем запрос с неверными данными (недопустимые ID)
        data = {'items': 'invalid_id'}
        response = self.client.delete(reverse('user-contact'), data, format='json')

        # Проверяем статус ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Используем response.json() для извлечения данных из JsonResponse
        response_data = response.json()

        # Проверяем, что ответ содержит сообщение об ошибке
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Не указаны все необходимые аргументы')

    def test_put_contact(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'id': contact.id, 'city': 'new_city'}
        response = self.client.put(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.get(id=contact.id).city, 'new_city')

    def test_put_contact_unauthenticated(self):
        self.client.logout()
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'id': contact.id, 'city': 'new_city'}
        response = self.client.put(reverse('user-contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_contact_invalid_data(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'id': contact.id}  # Передаём только ID, без других данных
        response = self.client.put(reverse('user-contact'), data, format='json')

        # Исправляем ожидаемый статус на 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = response.json()
        self.assertEqual(response_data['Status'], False)
        self.assertEqual(response_data['Errors'], 'Not all required arguments specified')


class TestOrderView(APITestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.view = OrderView.as_view()

    def test_get_orders_unauthenticated(self):
        request = self.factory.get('/orders/')
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_orders_authenticated(self):
        request = self.factory.get('/orders/')
        # Аутентифицируем пользователя
        force_authenticate(request, user=self.user)

        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_order_unauthenticated(self):
        request = self.factory.post('/orders/', {'id': 1, 'contact': 1})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_order_authenticated_invalid_data(self):
        request = self.factory.post('/orders/', {'id': 'a', 'contact': 1})
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_order_authenticated_valid_data(self):
        order = Order.objects.create(user_id=self.user.id, id=1)
        request = self.factory.post('/orders/', {'id': 1, 'contact': 1})
        force_authenticate(request, user=self.user)
        with patch.object(Order.objects, 'filter') as mock_filter:
            mock_filter.return_value.update.return_value = 1
            response = self.view(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_order_authenticated_integrity_error(self):
        order = Order.objects.create(user_id=self.user.id, id=1)
        request = self.factory.post('/orders/', {'id': 1, 'contact': 1})
        force_authenticate(request, user=self.user)
        with patch.object(Order.objects, 'filter') as mock_filter:
            mock_filter.return_value.update.side_effect = IntegrityError
            response = self.view(request)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
