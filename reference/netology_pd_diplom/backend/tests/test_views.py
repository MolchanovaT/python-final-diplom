import json
import unittest
from unittest.mock import patch

from backend.forms import LoadDataForm
from backend.models import Category, ProductParameter, Product
from backend.models import ConfirmEmailToken
from backend.models import Contact
from backend.models import Order
from backend.models import OrderItem, ProductInfo, Shop
from backend.models import TaskStatus
from backend.serializers import ContactSerializer
from backend.serializers import OrderSerializer
from backend.serializers import ShopSerializer
from backend.views import AccountDetails
from backend.views import ConfirmAccount
from backend.views import LoginAccount
from backend.views import OrderView
from backend.views import PartnerOrders
from backend.views import RegisterAccount
from backend.views import ShopView
from backend.views import run_task_view
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory, APITestCase
from django.test import TestCase, APIClient
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class TestRunTaskView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='testuser@example.com', password='password123')

    def test_run_task_view_get(self):
        request = self.factory.get('/run_task/')
        request.user = self.user
        response = run_task_view(request, shop_id=1)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context_data['form'], LoadDataForm)

    def test_run_task_view_post_valid_form(self):
        form_data = {'url': 'http://example.com'}
        request = self.factory.post('/run_task/', data=form_data)
        request.user = self.user
        response = run_task_view(request, shop_id=1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/backend/shop/')
        messages = [m.message for m in get_messages(request)]
        self.assertIn("Задача загружена в очередь", messages)
        task_status = TaskStatus.objects.get(user=self.user)
        self.assertEqual(task_status.status, 'PENDING')

    def test_run_task_view_post_invalid_form(self):
        form_data = {'url': 'invalid_url'}
        request = self.factory.post('/run_task/', data=form_data)
        request.user = self.user
        response = run_task_view(request, shop_id=1)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context_data['form'], LoadDataForm)
        self.assertEqual(response.context_data['form'].errors, {'url': ['Enter a valid URL.']})

    User = get_user_model()

    class TestRegisterAccount(TestCase):

        def setUp(self):
            self.factory = RequestFactory()

        def test_register_account_post_valid_data(self):
            data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'password': 'P@ssw0rd',
                'company': 'Test Company',
                'position': 'Test Position'
            }
            request = self.factory.post('/register', data=data, content_type='application/json')
            response = RegisterAccount.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['Status'], True)

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
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['Status'], False)
            self.assertIn('password', response.json()['Errors'])

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
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['Status'], False)
            self.assertEqual(response.json()['Errors'], 'Не указаны все необходимые аргументы')

        def test_register_account_post_invalid_serializer_data(self):
            data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'invalid_email',
                'password': 'P@ssw0rd',
                'company': 'Test Company',
                'position': 'Test Position'
            }
            request = self.factory.post('/register', data=data, content_type='application/json')
            response = RegisterAccount.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['Status'], False)
            self.assertIn('email', response.json()['Errors'])


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
            request.user = self.user
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
        self.user = User.objects.create_user(email='testuser@example.com', password='password123')

    def test_login_account_post_valid_credentials(self):
        data = {'email': 'testuser@example.com', 'password': 'password123'}
        request = self.factory.post(reverse('login'), data=data, content_type='application/json')
        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['Status'], True)

    def test_login_account_post_invalid_credentials(self):
        data = {'email': 'testuser@example.com', 'password': 'wrongpassword'}
        request = self.factory.post(reverse('login'), data=data, content_type='application/json')
        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['Status'], False)
        self.assertEqual(response.json()['Errors'], 'Не удалось авторизовать')

    def test_login_account_post_missing_credentials(self):
        data = {'email': 'testuser@example.com'}
        request = self.factory.post(reverse('login'), data=data, content_type='application/json')
        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['Status'], False)
        self.assertEqual(response.json()['Errors'], 'Not all required arguments specified')

    def test_login_account_post_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        data = {'email': 'testuser@example.com', 'password': 'password123'}
        request = self.factory.post(reverse('login'), data=data, content_type='application/json')
        response = LoginAccount.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['Status'], False)
        self.assertEqual(response.json()['Errors'], 'Failed to authorize')


class ShopViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ShopView.as_view()

    def test_get_shops(self):
        # Create a test shop
        test_shop = Shop.objects.create(name="Test Shop")

        # Make a GET request to the view
        request = self.factory.get('/shops/')
        response = self.view(request)

        # Check that the response is a success
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the response data is correct
        expected_data = ShopSerializer(test_shop).data
        self.assertEqual(response.data, [expected_data])

    def test_get_shops_empty(self):
        # Make a GET request to the view
        request = self.factory.get('/shops/')
        response = self.view(request)

        # Check that the response is a success
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the response data is correct
        self.assertEqual(response.data, [])

    def test_post_shops(self):
        # Create a test shop
        test_shop = Shop.objects.create(name="Test Shop")

        # Make a POST request to the view
        request = self.factory.post('/shops/', {'name': 'New Shop'})
        response = self.view(request)

        # Check that the response is a success
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the response data is correct
        expected_data = ShopSerializer(test_shop).data
        self.assertEqual(response.data, expected_data)

    def test_post_shops_invalid_data(self):
        # Make a POST request to the view with invalid data
        request = self.factory.post('/shops/', {'invalid_field': 'Invalid Value'})
        response = self.view(request)

        # Check that the response is a failure
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check that the response data is correct
        self.assertEqual(response.data, {'name': ['This field is required.']})


class ProductInfoViewTests(APITestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name='Test Shop', state=True)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product_info = ProductInfo.objects.create(shop=self.shop, product=self.product)

    def test_get_product_info(self):
        url = reverse('product-info')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_shop_id(self):
        url = reverse('product-info')
        response = self.client.get(url, {'shop_id': self.shop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_category_id(self):
        url = reverse('product-info')
        response = self.client.get(url, {'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_shop_id_and_category_id(self):
        url = reverse('product-info')
        response = self.client.get(url, {'shop_id': self.shop.id, 'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_product_info_with_invalid_shop_id(self):
        url = reverse('product-info')
        response = self.client.get(url, {'shop_id': 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_product_info_with_invalid_category_id(self):
        url = reverse('product-info')
        response = self.client.get(url, {'category_id': 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class BasketViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = self.create_user()
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name='Test Category')
        self.shop = Shop.objects.create(name='Test Shop', state=True)
        self.product_info = ProductInfo.objects.create(shop=self.shop, category=self.category, name='Test Product')
        self.product = Product.objects.create(name='Test Product')
        self.product_parameter = ProductParameter.objects.create(parameter_name='Test Parameter', value='Test Value')
        self.product_info.product_parameters.add(self.product_parameter)
        self.product_info.product = self.product

        self.order = Order.objects.create(user_id=self.user.id, state='basket')
        self.order_item = OrderItem.objects.create(order=self.order, product_info=self.product_info, quantity=1)

    def create_user(self):
        user_data = {
            'username': 'test_user',
            'password': 'test_password',
            'email': 'test@example.com'
        }
        return self.client.post(reverse('user-register'), user_data, format='json').data

    def test_get_basket(self):
        response = self.client.get(reverse('basket'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_post_basket(self):
        data = {
            'items': json.dumps([{'product_info': self.product_info.id, 'quantity': 1}])
        }
        response = self.client.post(reverse('basket'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['Создано объектов'], 1)

    def test_post_basket_invalid_data(self):
        data = {
            'items': json.dumps([{'invalid_field': 'Invalid Value'}])
        }
        response = self.client.post(reverse('basket'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_basket(self):
        data = {
            'items': str(self.order_item.id)
        }
        response = self.client.delete(reverse('basket'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Удалено объектов'], 1)

    def test_put_basket(self):
        data = {
            'items': json.dumps([{'id': self.order_item.id, 'quantity': 2}])
        }
        response = self.client.put(reverse('basket'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Обновлено объектов'], 1)


class TestPartnerUpdateView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
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
        self.assertEqual(response.json(), {'Status': False, 'Errors': 'Not all required arguments specified'})

    def test_partner_state_post_authenticated_invalid_state(self):
        self.factory.force_authenticate(user=self.user)
        response = self.factory.post(reverse('partner-state'), data={'state': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'Status': False, 'Errors': 'invalid is not a valid boolean value'})

    def test_partner_state_post_authenticated_valid_state(self):
        self.factory.force_authenticate(user=self.user)
        response = self.factory.post(reverse('partner-state'), data={'state': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'Status': True})


class PartnerOrdersTestCase(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='testuser@example.com', password='password123', type='shop')
        self.user.shop = Shop.objects.create(name='Test Shop')
        self.user.save()
        self.order = Order.objects.create(user=self.user, state='new')
        self.order_item = OrderItem.objects.create(order=self.order,
                                                   product_info=ProductInfo.objects.create(shop=self.user.shop),
                                                   quantity=1)
        self.partner_orders = PartnerOrders()

    def test_get_unauthenticated(self):
        request = self.factory.get('/partner/orders')
        response = self.partner_orders.get(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Log in required'})

    def test_get_not_shop(self):
        not_shop_user = User.objects.create_user(email='testuser2@example.com', password='password123', type='not_shop')
        request = self.factory.get('/partner/orders')
        self.factory.force_authenticate(user=not_shop_user)
        response = self.partner_orders.get(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Только для магазинов'})

    @patch('backend.views.Order.objects.filter')
    def test_get_valid(self, mock_filter):
        mock_filter.return_value = [self.order]
        request = self.factory.get('/partner/orders')
        self.factory.force_authenticate(user=self.user)
        response = self.partner_orders.get(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), dict)
        serializer = OrderSerializer(self.order, many=False)
        self.assertEqual(response.json(), serializer.data)

    @patch('backend.views.Order.objects.filter')
    def test_get_invalid(self, mock_filter):
        mock_filter.return_value = []
        request = self.factory.get('/partner/orders')
        self.factory.force_authenticate(user=self.user)
        response = self.partner_orders.get(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), dict)
        self.assertEqual(response.json(), [])


class TestContactView(APITestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_contact(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        response = self.client.get(reverse('contact'))
        serializer = ContactSerializer(contact)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [serializer.data])

    def test_get_contact_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_contact(self):
        data = {'city': 'city', 'street': 'street', 'phone': 'phone'}
        response = self.client.post(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.count(), 1)

    def test_post_contact_unauthenticated(self):
        self.client.logout()
        data = {'city': 'city', 'street': 'street', 'phone': 'phone'}
        response = self.client.post(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_contact_invalid_data(self):
        data = {'city': 'city', 'street': 'street'}
        response = self.client.post(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(response.data['Errors'], 'Не указаны все необходимые аргументы')

    def test_delete_contact(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'items': str(contact.id)}
        response = self.client.delete(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.count(), 0)

    def test_delete_contact_unauthenticated(self):
        self.client.logout()
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'items': str(contact.id)}
        response = self.client.delete(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_contact_invalid_data(self):
        data = {'items': 'invalid_id'}
        response = self.client.delete(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(response.data['Errors'], 'Not all required arguments specified')

    def test_put_contact(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'id': contact.id, 'city': 'new_city'}
        response = self.client.put(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.get(id=contact.id).city, 'new_city')

    def test_put_contact_unauthenticated(self):
        self.client.logout()
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'id': contact.id, 'city': 'new_city'}
        response = self.client.put(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_contact_invalid_data(self):
        contact = Contact.objects.create(user=self.user, city='city', street='street', phone='phone')
        data = {'id': contact.id}
        response = self.client.put(reverse('contact'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(response.data['Errors'], 'Not all required arguments specified')


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
        request.user = self.user
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_order_unauthenticated(self):
        request = self.factory.post('/orders/', {'id': 1, 'contact': 1})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_order_authenticated_invalid_data(self):
        request = self.factory.post('/orders/', {'id': 'a', 'contact': 1})
        request.user = self.user
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_order_authenticated_valid_data(self):
        order = Order.objects.create(user_id=self.user.id, id=1)
        request = self.factory.post('/orders/', {'id': 1, 'contact': 1})
        request.user = self.user
        with patch.object(Order.objects, 'filter') as mock_filter:
            mock_filter.return_value.update.return_value = 1
            response = self.view(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_order_authenticated_integrity_error(self):
        order = Order.objects.create(user_id=self.user.id, id=1)
        request = self.factory.post('/orders/', {'id': 1, 'contact': 1})
        request.user = self.user
        with patch.object(Order.objects, 'filter') as mock_filter:
            mock_filter.return_value.update.side_effect = IntegrityError
            response = self.view(request)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
