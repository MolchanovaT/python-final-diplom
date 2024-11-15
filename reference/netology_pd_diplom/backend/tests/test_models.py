from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from backend.models import (
    Shop, Category, Product, ProductInfo, Parameter,
    ProductParameter, Contact, Order, OrderItem, ConfirmEmailToken, TaskStatus
)

User = get_user_model()


class UserModelTests(TestCase):

    def test_user_creation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('password123'))

    def test_superuser_creation(self):
        superuser = User.objects.create_superuser(email='admin@example.com', password='admin123')
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)


class ShopModelTests(TestCase):

    def test_shop_creation(self):
        user = User.objects.create_user(email='shopowner@example.com', password='password123')
        shop = Shop.objects.create(name="Test Shop", user=user)
        self.assertEqual(shop.name, "Test Shop")
        self.assertEqual(shop.user, user)


class CategoryModelTests(TestCase):

    def test_category_creation(self):
        category = Category.objects.create(name="Electronics")
        self.assertEqual(category.name, "Electronics")


class ProductModelTests(TestCase):

    def test_product_creation(self):
        category = Category.objects.create(name="Electronics")
        product = Product.objects.create(name="Smartphone", category=category)
        self.assertEqual(product.name, "Smartphone")
        self.assertEqual(product.category, category)


class ProductInfoModelTests(TestCase):

    def test_product_info_creation(self):
        category = Category.objects.create(name="Electronics")
        product = Product.objects.create(name="Smartphone", category=category)
        shop = Shop.objects.create(name="Test Shop")
        product_info = ProductInfo.objects.create(
            product=product, shop=shop, external_id=1, quantity=10, price=1000, price_rrc=1200
        )
        self.assertEqual(product_info.product, product)
        self.assertEqual(product_info.shop, shop)
        self.assertEqual(product_info.quantity, 10)


class ParameterModelTests(TestCase):

    def test_parameter_creation(self):
        parameter = Parameter.objects.create(name="Color")
        self.assertEqual(parameter.name, "Color")


class ProductParameterModelTests(TestCase):

    def test_product_parameter_creation(self):
        parameter = Parameter.objects.create(name="Color")
        product_info = ProductInfo.objects.create(
            product=Product.objects.create(name="Smartphone"),
            shop=Shop.objects.create(name="Shop"),
            external_id=1,
            quantity=5,
            price=1000,
            price_rrc=1100
        )
        product_parameter = ProductParameter.objects.create(
            product_info=product_info, parameter=parameter, value="Black"
        )
        self.assertEqual(product_parameter.parameter, parameter)
        self.assertEqual(product_parameter.value, "Black")


class ContactModelTests(TestCase):

    def test_contact_creation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        contact = Contact.objects.create(
            user=user, city="New York", street="5th Avenue", phone="+123456789"
        )
        self.assertEqual(contact.city, "New York")
        self.assertEqual(contact.user, user)


class OrderModelTests(TestCase):

    def test_order_creation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        order = Order.objects.create(user=user, state="new")
        self.assertEqual(order.state, "new")
        self.assertEqual(order.user, user)


class OrderItemModelTests(TestCase):

    def test_order_item_creation(self):
        order = Order.objects.create(user=User.objects.create_user(email='user@example.com', password='password'))
        product_info = ProductInfo.objects.create(
            product=Product.objects.create(name="Laptop"),
            shop=Shop.objects.create(name="Shop"),
            external_id=2,
            quantity=3,
            price=2000,
            price_rrc=2200
        )
        order_item = OrderItem.objects.create(order=order, product_info=product_info, quantity=1)
        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.product_info, product_info)
        self.assertEqual(order_item.quantity, 1)


class ConfirmEmailTokenTests(TestCase):

    @patch("backend.signals.send_registration_confirmation.delay")  # Мокаем вызов задачи
    def test_confirm_email_token_creation(self, mock_send_confirmation):
        """
        Тестируем, что сигнал вызывает задачу Celery при создании нового пользователя.
        """
        user = User.objects.create_user(email='testuser@example.com', password='password123')

        # Проверяем, что задача отправки подтверждения была вызвана
        mock_send_confirmation.assert_called_once_with(user_id=user.id)


class TaskStatusModelTests(TestCase):

    def test_task_status_creation(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus.objects.create(user=user, task_id="abc123", status="PENDING")
        self.assertEqual(task_status.status, "PENDING")
        self.assertEqual(task_status.user, user)
