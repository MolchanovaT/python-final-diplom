from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from backend.models import (
    Shop, Category, Product, ProductInfo, Parameter,
    ProductParameter, Contact, Order, OrderItem, ConfirmEmailToken, TaskStatus, STATE_CHOICES
)

User = get_user_model()


class TestUserManager(TestCase):

    def test_create_user(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('password123'))

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(email='admin@example.com', password='admin123')
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    def test_create_user_with_no_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='password123')

    def test_create_superuser_with_false_is_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email='admin@example.com', password='admin123', is_staff=False)

    def test_create_superuser_with_false_is_superuser(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email='admin@example.com', password='admin123', is_superuser=False)


class TestUserModel(TestCase):

    def test_user_creation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('password123'))

    def test_superuser_creation(self):
        superuser = User.objects.create_superuser(email='admin@example.com', password='admin123')
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    def test_user_type_default(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.assertEqual(user.type, 'buyer')

    def test_user_type_choice(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123', type='shop')
        self.assertEqual(user.type, 'shop')

    def test_user_is_active_default(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.assertFalse(user.is_active)

    def test_user_is_active_set(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123', is_active=True)
        self.assertTrue(user.is_active)

    def test_user_str_representation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123', first_name='John',
                                        last_name='Doe')
        self.assertEqual(str(user), 'John Doe')


class ShopModelTests(TestCase):

    def test_shop_creation(self):
        shop = Shop.objects.create(name="Test Shop")
        self.assertEqual(shop.name, "Test Shop")

    def test_shop_name_max_length(self):
        shop = Shop.objects.create(name="a" * 51)
        with self.assertRaises(ValidationError):
            shop.full_clean()

    def test_shop_url_is_optional(self):
        shop = Shop.objects.create(name="Test Shop")
        self.assertIsNone(shop.url)

    def test_shop_user_is_optional(self):
        shop = Shop.objects.create(name="Test Shop")
        self.assertIsNone(shop.user)

    def test_shop_state_default(self):
        shop = Shop.objects.create(name="Test Shop")
        self.assertTrue(shop.state)

    def test_shop_verbose_name(self):
        self.assertEqual(Shop._meta.verbose_name, 'Магазин')

    def test_shop_verbose_name_plural(self):
        self.assertEqual(Shop._meta.verbose_name_plural, "Список магазинов")

    def test_shop_ordering(self):
        shop1 = Shop.objects.create(name="Test Shop 1")
        shop2 = Shop.objects.create(name="Test Shop 2")

        # Получаем объекты в порядке, указанном в Meta: ordering = ('-name',)
        shops = Shop.objects.all()

        # Проверяем, что shop2 находится раньше shop1 (т.к. сортировка по name в порядке убывания)
        self.assertEqual(list(shops), [shop2, shop1])

    def test_shop_str_representation(self):
        shop = Shop.objects.create(name="Test Shop")
        self.assertEqual(str(shop), "Test Shop")


class CategoryModelTests(TestCase):

    def test_category_creation(self):
        category = Category.objects.create(name="Electronics")
        self.assertEqual(category.name, "Electronics")

    def test_category_shops(self):
        category = Category.objects.create(name="Electronics")
        shop1 = Shop.objects.create(name="Shop1")
        shop2 = Shop.objects.create(name="Shop2")
        category.shops.add(shop1, shop2)
        self.assertEqual(category.shops.count(), 2)

    def test_category_str(self):
        category = Category.objects.create(name="Electronics")
        self.assertEqual(str(category), "Electronics")

    def test_category_verbose_name(self):
        self.assertEqual(Category._meta.verbose_name, 'Категория')

    def test_category_verbose_name_plural(self):
        self.assertEqual(Category._meta.verbose_name_plural, "Список категорий")

    def test_category_ordering(self):
        category1 = Category.objects.create(name="Electronics")
        category2 = Category.objects.create(name="Books")

        # Порядок должен быть в убывающем порядке, согласно Meta: ordering = ('-name',)
        categories = Category.objects.all()
        self.assertEqual(categories[0], category1)  # Electronics должно быть первым
        self.assertEqual(categories[1], category2)  # Books должно быть вторым


class ProductModelTests(TestCase):

    def test_product_creation(self):
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(product.category.name, 'Test Category')

    def test_product_verbose_name(self):
        category = Category.objects.create(name='Test Category')  # Создаем категорию
        product = Product.objects.create(name='Test Product', category=category)  # Указываем category
        self.assertEqual(product._meta.verbose_name, 'Продукт')

    def test_product_verbose_name_plural(self):
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        self.assertEqual(product._meta.verbose_name_plural, "Список продуктов")

    def test_product_ordering(self):
        category = Category.objects.create(name='Test Category')
        Product.objects.create(name='Product A', category=category)
        Product.objects.create(name='Product B', category=category)
        products = Product.objects.all()
        self.assertEqual(products[0].name, 'Product B')
        self.assertEqual(products[1].name, 'Product A')

    def test_product_str_representation(self):
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        self.assertEqual(str(product), 'Test Product')


class ProductInfoModelTests(TestCase):

    def test_product_info_creation(self):
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        shop = Shop.objects.create(name="Test Shop")
        product_info = ProductInfo.objects.create(
            product=product, shop=shop, external_id=1, quantity=10, price=1000, price_rrc=1200
        )
        self.assertEqual(product_info.product, product)
        self.assertEqual(product_info.shop, shop)
        self.assertEqual(product_info.quantity, 10)

    def test_product_info_unique_constraint(self):
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        shop = Shop.objects.create(name="Test Shop")
        ProductInfo.objects.create(
            product=product, shop=shop, external_id=1, quantity=10, price=1000, price_rrc=1200
        )
        with self.assertRaises(IntegrityError):
            ProductInfo.objects.create(
                product=product, shop=shop, external_id=1, quantity=10, price=1000, price_rrc=1200
            )

    def test_product_info_blank_fields(self):
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        shop = Shop.objects.create(name="Test Shop")
        product_info = ProductInfo.objects.create(
            product=product, shop=shop, external_id=1, quantity=10, price=1000, price_rrc=1200, model=""
        )
        self.assertEqual(product_info.model, "")

    def test_product_info_verbose_name(self):
        self.assertEqual(ProductInfo._meta.verbose_name, 'Информация о продукте')

    def test_product_info_verbose_name_plural(self):
        self.assertEqual(ProductInfo._meta.verbose_name_plural, "Информационный список о продуктах")


class ParameterModelTests(TestCase):

    def test_parameter_creation(self):
        parameter = Parameter.objects.create(name="Color")
        self.assertEqual(parameter.name, "Color")

    def test_parameter_verbose_name(self):
        parameter = Parameter.objects.create(name="Color")
        self.assertEqual(parameter._meta.verbose_name, 'Имя параметра')

    def test_parameter_verbose_name_plural(self):
        parameter = Parameter.objects.create(name="Color")
        self.assertEqual(parameter._meta.verbose_name_plural, "Список имен параметров")

    def test_parameter_ordering(self):
        Parameter.objects.create(name="Color")
        Parameter.objects.create(name="Size")
        parameters = Parameter.objects.all()
        self.assertEqual(parameters[0].name, "Size")
        self.assertEqual(parameters[1].name, "Color")

    def test_parameter_str_representation(self):
        parameter = Parameter.objects.create(name="Color")
        self.assertEqual(str(parameter), "Color")


class ProductParameterModelTests(TestCase):

    def setUp(self):
        # Создаем объект Category
        self.category = Category.objects.create(name='Test Category')

        # Создаем объект Product (продукт), указывая категорию
        self.product = Product.objects.create(name='Test Product', category=self.category)

        # Создаем объект Shop (магазин)
        self.shop = Shop.objects.create(name='Test Shop')

        # Создаем объект ProductInfo с обязательным полем quantity
        self.product_info = ProductInfo.objects.create(
            model='Test Model',
            external_id=1,
            product=self.product,
            shop=self.shop,
            quantity=10,  # Передаем обязательное поле quantity
            price=1000,
            price_rrc=1200
        )

        # Создаем объект Parameter (параметр)
        self.parameter = Parameter.objects.create(name='Test Parameter')

    def test_product_parameter_creation(self):
        product_parameter = ProductParameter.objects.create(product_info=self.product_info, parameter=self.parameter,
                                                            value='Test Value')
        self.assertEqual(product_parameter.product_info, self.product_info)
        self.assertEqual(product_parameter.parameter, self.parameter)
        self.assertEqual(product_parameter.value, 'Test Value')

    def test_unique_product_parameter_constraint(self):
        ProductParameter.objects.create(product_info=self.product_info, parameter=self.parameter, value='Test Value')
        with self.assertRaises(IntegrityError):
            ProductParameter.objects.create(product_info=self.product_info, parameter=self.parameter,
                                            value='Another Value')

    def test_product_info_required(self):
        with self.assertRaises(IntegrityError):
            ProductParameter.objects.create(parameter=self.parameter, value='Test Value')

    def test_parameter_required(self):
        with self.assertRaises(IntegrityError):
            ProductParameter.objects.create(product_info=self.product_info, value='Test Value')


class ContactModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="password123")

    def test_contact_creation(self):
        contact = Contact.objects.create(user=self.user, city="Test City", street="Test Street", phone="123456789")
        self.assertEqual(contact.user, self.user)
        self.assertEqual(contact.city, "Test City")
        self.assertEqual(contact.street, "Test Street")
        self.assertEqual(contact.phone, "123456789")

    def test_contact_verbose_name(self):
        self.assertEqual(Contact._meta.verbose_name, 'Контакты пользователя')

    def test_contact_verbose_name_plural(self):
        self.assertEqual(Contact._meta.verbose_name_plural, "Список контактов пользователя")

    def test_contact_str_representation(self):
        contact = Contact.objects.create(user=self.user, city="Test City", street="Test Street", house="Test House",
                                         phone="123456789")
        self.assertEqual(str(contact), f'{contact.city} {contact.street} {contact.house}')

    def test_contact_blank_fields(self):
        contact = Contact.objects.create(user=self.user, city="Test City", street="Test Street", phone="123456789")
        self.assertEqual(contact.house, "")
        self.assertEqual(contact.structure, "")
        self.assertEqual(contact.building, "")
        self.assertEqual(contact.apartment, "")


class OrderModelTests(TestCase):

    def test_order_state_choices(self):
        user = User.objects.create_user(email="testuser@example.com", password="password123")
        order = Order.objects.create(user=user, state="new")
        self.assertIn(order.state, [choice[0] for choice in STATE_CHOICES])  # Ссылаемся на глобальный STATE_CHOICES

    def test_order_creation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        order = Order.objects.create(user=user, state="new")
        self.assertEqual(order.state, "new")
        self.assertEqual(order.user, user)

    def test_order_contact_required(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        order = Order.objects.create(user=user, state="new", contact=None)  # Создаем заказ без контакта
        self.assertIsNone(order.contact)  # Проверяем, что поле contact может быть пустым

    def test_order_verbose_name(self):
        self.assertEqual(Order._meta.verbose_name, 'Заказ')

    def test_order_verbose_name_plural(self):
        self.assertEqual(Order._meta.verbose_name_plural, "Список заказ")

    def test_order_ordering(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        order1 = Order.objects.create(user=user, state="new")
        order2 = Order.objects.create(user=user, state="new")
        orders = Order.objects.all()
        self.assertEqual(orders[0].dt, order2.dt)
        self.assertEqual(orders[1].dt, order1.dt)

    def test_order_str_representation(self):
        user = User.objects.create_user(email='testuser@example.com', password='password123')
        order = Order.objects.create(user=user, state="new")
        self.assertEqual(str(order), str(order.dt))


class OrderItemModelTests(TestCase):

    def setUp(self):
        # Создаем категорию
        self.category = Category.objects.create(name='Test Category')

        # Создаем продукт
        self.product = Product.objects.create(name='Test Product', category=self.category)

        # Создаем магазин
        self.shop = Shop.objects.create(name='Test Shop')

        # Создаем информацию о продукте с обязательным полем `quantity`
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=1,
            quantity=10,  # Указываем значение
            price=1000,
            price_rrc=1200
        )

        # Создаем пользователя
        self.user = User.objects.create_user(email="testuser@example.com", password="password123")

        # Создаем заказ
        self.order = Order.objects.create(user=self.user, state="new")

    def test_order_item_creation(self):
        order_item = OrderItem.objects.create(order=self.order, product_info=self.product_info, quantity=10)
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.product_info, self.product_info)
        self.assertEqual(order_item.quantity, 10)

    def test_order_item_unique_constraint(self):
        OrderItem.objects.create(order=self.order, product_info=self.product_info, quantity=10)
        with self.assertRaises(IntegrityError):
            OrderItem.objects.create(order=self.order, product_info=self.product_info, quantity=10)

    def test_order_required(self):
        with self.assertRaises(IntegrityError):
            OrderItem.objects.create(product_info=self.product_info, quantity=10)

    def test_product_info_required(self):
        with self.assertRaises(IntegrityError):
            OrderItem.objects.create(order=self.order, quantity=10)

    def test_order_item_verbose_name(self):
        self.assertEqual(OrderItem._meta.verbose_name, 'Заказанная позиция')

    def test_order_item_verbose_name_plural(self):
        self.assertEqual(OrderItem._meta.verbose_name_plural, "Список заказанных позиций")


class ConfirmEmailTokenModelTests(TestCase):

    def test_confirm_email_token_creation(self):
        user = User.objects.create_user(email="testuser@example.com", password="password123")
        confirm_email_token = ConfirmEmailToken.objects.create(user=user)
        self.assertEqual(confirm_email_token.user, user)

    def test_confirm_email_token_verbose_name(self):
        confirm_email_token = ConfirmEmailToken.objects.create(
            user=User.objects.create_user(email="testuser@example.com", password="password123"))
        self.assertEqual(confirm_email_token._meta.verbose_name, 'Токен подтверждения Email')

    def test_confirm_email_token_verbose_name_plural(self):
        confirm_email_token = ConfirmEmailToken.objects.create(
            user=User.objects.create_user(email="testuser@example.com", password="password123"))
        self.assertEqual(confirm_email_token._meta.verbose_name_plural, 'Токены подтверждения Email')

    def test_confirm_email_token_generate_key(self):
        confirm_email_token = ConfirmEmailToken()
        key = confirm_email_token.generate_key()
        self.assertIsNotNone(key)

    def test_confirm_email_token_save(self):
        user = User.objects.create_user(email="testuser@example.com", password="password123")
        confirm_email_token = ConfirmEmailToken(user=user)
        confirm_email_token.save()
        self.assertIsNotNone(confirm_email_token.key)

    def test_confirm_email_token_str_representation(self):
        user = User.objects.create_user(email="testuser@example.com", password="password123")
        confirm_email_token = ConfirmEmailToken.objects.create(user=user)
        self.assertEqual(str(confirm_email_token), f"Password reset token for user {user}")


class TaskStatusModelTests(TestCase):

    def test_task_status_creation(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus.objects.create(user=user, task_id="abc123", status="PENDING")
        self.assertEqual(task_status.status, "PENDING")
        self.assertEqual(task_status.user, user)

    def test_task_status_verbose_name(self):
        self.assertEqual(TaskStatus._meta.verbose_name, 'Статус запущенных задач')

    def test_task_status_str_representation(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus.objects.create(user=user, task_id="abc123", status="PENDING")
        self.assertEqual(str(task_status), f'Задача {task_status.task_id} - {task_status.status}')

    def test_task_status_user_required(self):
        with self.assertRaises(IntegrityError):
            TaskStatus.objects.create(task_id="abc123", status="PENDING")

    def test_task_status_task_id_required(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus(user=user, status="PENDING")  # Не передаем task_id
        with self.assertRaises(ValidationError):
            task_status.full_clean()  # Проведение валидации модели

    def test_task_status_status_default(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus.objects.create(user=user, task_id="abc123")
        self.assertEqual(task_status.status, "PENDING")

    def test_task_status_created_at_auto_now_add(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus.objects.create(user=user, task_id="abc123", status="PENDING")
        self.assertIsNotNone(task_status.created_at)

    def test_task_status_updated_at_auto_now(self):
        user = User.objects.create_user(email='user@example.com', password='password123')
        task_status = TaskStatus.objects.create(user=user, task_id="abc123", status="PENDING")
        self.assertIsNotNone(task_status.updated_at)
