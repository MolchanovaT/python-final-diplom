from django.test import TestCase
from backend.models import User, Contact, Category, Shop, Product, ProductInfo, ProductParameter, Order, OrderItem
from backend.serializers import (
    ContactSerializer, UserSerializer, CategorySerializer, ShopSerializer,
    ProductSerializer, ProductParameterSerializer, ProductInfoSerializer,
    OrderItemSerializer, OrderSerializer
)


class ContactSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="testuser@example.com")
        self.contact_data = {
            "city": "Moscow",
            "street": "Red Square",
            "house": "1",
            "structure": "",
            "building": "",
            "apartment": "101",
            "user": self.user.id,
            "phone": "1234567890"
        }
        self.serializer = ContactSerializer(data=self.contact_data)

    def test_contact_serializer_valid(self):
        self.assertTrue(self.serializer.is_valid())

    def test_contact_serializer_fields(self):
        self.serializer.is_valid()
        self.assertEqual(set(self.serializer.data.keys()), {"id", "city", "street", "house", "structure", "building", "apartment", "phone"})


class UserSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="testuser@example.com", first_name="Test", last_name="User")
        self.serializer = UserSerializer(instance=self.user)

    def test_user_serializer_fields(self):
        self.assertEqual(set(self.serializer.data.keys()), {"id", "first_name", "last_name", "email", "company", "position", "contacts"})


class CategorySerializerTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.serializer = CategorySerializer(instance=self.category)

    def test_category_serializer_fields(self):
        self.assertEqual(set(self.serializer.data.keys()), {"id", "name"})


class ShopSerializerTest(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="SuperShop", state=True)
        self.serializer = ShopSerializer(instance=self.shop)

    def test_shop_serializer_fields(self):
        self.assertEqual(set(self.serializer.data.keys()), {"id", "name", "state"})


class ProductSerializerTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(name="Laptop", category=self.category)
        self.serializer = ProductSerializer(instance=self.product)

    def test_product_serializer_fields(self):
        self.assertEqual(set(self.serializer.data.keys()), {"name", "category"})


class OrderSerializerTest(TestCase):

    def setUp(self):
        """
        Создаем базовые данные для тестов.
        """
        # Создаем пользователя
        self.user = User.objects.create(email="testuser@example.com")

        # Создаем контакт
        self.contact = Contact.objects.create(user=self.user, city="Moscow", street="Main Street", phone="1234567890")

        # Создаем заказ
        self.order = Order.objects.create(user=self.user, state="new", contact=self.contact, total_sum=1000)

        # Создаем информацию о продукте
        self.product_info = ProductInfo.objects.create(
            product_id=1, shop_id=1, external_id=1, quantity=10, price=100, price_rrc=120
        )

        # Создаем заказанную позицию
        self.order_item = OrderItem.objects.create(
            order=self.order, product_info=self.product_info, quantity=2
        )

        # Сериализуем заказ
        self.serializer = OrderSerializer(instance=self.order)

    def test_order_serializer_fields(self):
        """
        Проверяем, что сериализатор возвращает правильные поля для Order.
        """
        expected_fields = {"id", "ordered_items", "state", "dt", "total_sum", "contact"}
        actual_fields = set(self.serializer.data.keys())

        self.assertEqual(actual_fields, expected_fields)

    def test_order_serializer_data(self):
        """
        Проверяем, что сериализатор правильно возвращает данные для заказа.
        """
        data = self.serializer.data

        # Проверяем правильность данных для полей
        self.assertEqual(data["id"], self.order.id)
        self.assertEqual(data["total_sum"], self.order.total_sum)
        self.assertEqual(data["state"], self.order.state)
        self.assertEqual(data["contact"]["id"], self.contact.id)
        self.assertEqual(data["ordered_items"][0]["id"], self.order_item.id)
        self.assertEqual(data["ordered_items"][0]["product_info"], self.product_info.id)
        self.assertEqual(data["ordered_items"][0]["quantity"], self.order_item.quantity)

    def test_order_serializer_read_only_fields(self):
        """
        Проверяем, что поля, которые должны быть read-only, действительно являются таковыми.
        """
        read_only_fields = {"id"}
        for field in read_only_fields:
            self.assertIn(field, self.serializer.fields)
            self.assertTrue(self.serializer.fields[field].read_only)

    def test_order_serializer_contact_read_only(self):
        """
        Проверяем, что поле 'contact' является read-only.
        """
        self.assertTrue(self.serializer.fields["contact"].read_only)
