import json
from distutils.util import strtobool
from rest_framework.request import Request
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from backend.tasks import load_data_from_url

from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, TaskStatus
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer
from backend.signals import new_user_registered, new_order

from django.shortcuts import redirect, render
from django.contrib import admin, messages
from django.contrib.auth.decorators import login_required

from backend.forms import LoadDataForm


@login_required  # Требует аутентифицированного пользователя
def run_task_view(request):
    if request.method == "POST":
        form = LoadDataForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']

            # Запускаем асинхронную задачу
            task = load_data_from_url.apply_async(args=[url])

            # Создаем запись TaskStatus для текущего пользователя
            TaskStatus.objects.create(
                user=request.user,  # Указываем аутентифицированного пользователя
                task_id=task.id,
                status="PENDING"
            )

            # Устанавливаем сообщение и редиректим
            messages.success(request, "Задача загружена в очередь")
            return redirect('/admin/backend/shop/')
    else:
        form = LoadDataForm()

    return render(request, "run_task_form.html", {"form": form})


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    # Регистрация методом POST

    def post(self, request, *args, **kwargs):
        """
        Process a POST request and create a new user.

        Args:
            request (Request): The Django request object.

        Returns:
            JsonResponse: The response indicating the status of the operation and any errors.
        """
        # Проверяем обязательные аргументы
        required_fields = {'first_name', 'last_name', 'email', 'password', 'company', 'position'}
        if not required_fields.issubset(request.data):
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

        # Проверяем данные сериализатора
        user_serializer = UserSerializer(data=request.data)
        if not user_serializer.is_valid():
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        # Проверяем пароль на сложность
        try:
            validate_password(request.data['password'])
        except Exception as password_error:
            error_array = []
            for item in password_error:
                error_array.append(item)
            return JsonResponse({'Status': False, 'Errors': {'password': error_array}})

        # Создаём пользователя
        user = user_serializer.save()
        user.set_password(request.data['password'])
        user.save()

        return JsonResponse({'Status': True})


class ConfirmAccount(APIView):
    def post(self, request, *args, **kwargs):
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True}, json_dumps_params={
                    'ensure_ascii': False})  # Устанавливаем параметр в json_dumps_params
            else:
                return JsonResponse({'Status': False, 'Errors': 'Wrong token or email'},
                                    json_dumps_params={'ensure_ascii': False})

        return JsonResponse({'Status': False, 'Errors': 'Not all required arguments specified'},
                            json_dumps_params={'ensure_ascii': False})


class AccountDetails(APIView):
    """
    A class for managing user account details.

    Methods:
    - get: Retrieve the details of the authenticated user.
    - post: Update the account details of the authenticated user.

    Attributes:
    - None
    """

    # получить данные
    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the details of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the authenticated user.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        """
                Update the account details of the authenticated user.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        # проверяем обязательные аргументы

        if 'password' in request.data:
            errors = {}
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    # Авторизация методом POST
    def post(self, request, *args, **kwargs):
        """
                Authenticate a user.

                Args:
                    request (Request): The Django request object.

                Returns:
                    JsonResponse: The response indicating the status of the operation and any errors.
                """
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
        A class for searching products.

        Methods:
        - get: Retrieve the product information based on the specified filters.

        Attributes:
        - None
        """

    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the product information based on the specified filters.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the product information.
               """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дуликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class BasketView(APIView):
    """
    A class for managing the user's shopping basket.

    Methods:
    - get: Retrieve the items in the user's basket.
    - post: Add an item to the user's basket.
    - put: Update the quantity of an item in the user's basket.
    - delete: Remove an item from the user's basket.

    Attributes:
    - None
    """

    # получить корзину
    def get(self, request, *args, **kwargs):
        """
                Retrieve the items in the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - Response: The response containing the items in the user's basket.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # редактировать корзину

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            try:
                items_dict = json.loads(items_string)  # Заменила load_json на стандартный json.loads
                if not isinstance(items_dict, list):  # Проверяем, что передан список объектов
                    raise ValueError("Items должны быть списком")
            except (ValueError, TypeError) as e:
                return JsonResponse({'Status': False, 'Errors': f'Неверный формат запроса: {str(e)}'}, status=400)
            with transaction.atomic():
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    if 'product_info' not in order_item or 'quantity' not in order_item:
                        return JsonResponse(
                            {'Status': False,
                             'Errors': 'Поля product_info и quantity обязательны для каждого элемента'},
                            status=400
                        )

                    try:
                        order_item.update({'order': basket.id})
                        existing_item = OrderItem.objects.filter(order=basket,
                                                                 product_info_id=order_item.get('product_info')).first()
                        if existing_item:
                            existing_item.quantity += order_item.get('quantity', 0)
                            existing_item.save()
                        else:
                            serializer = OrderItemSerializer(data=order_item)
                            if serializer.is_valid():
                                serializer.save()
                                objects_created += 1
                            else:
                                return JsonResponse({'Status': False, 'Errors': serializer.errors}, status=400)

                    except Exception as e:
                        return JsonResponse({'Status': False, 'Errors': f'Ошибка обработки элемента: {str(e)}'},
                                            status=400)
                return JsonResponse({'Status': True, 'Создано объектов': objects_created}, status=201)
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        """
                Remove  items from the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # добавить позиции в корзину
    def put(self, request, *args, **kwargs):
        """
        Update the items in the user's basket.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            try:
                # Десериализация строки JSON в список словарей
                items_dict = load_json(items_string)
                if not isinstance(items_dict, list):
                    raise ValueError("Invalid format: 'items' must be a list of dictionaries.")
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    # Убедимся, что оба поля ('id' и 'quantity') присутствуют и корректны
                    if isinstance(order_item.get('id'), int) and isinstance(order_item.get('quantity'), int):
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])
                    else:
                        return JsonResponse({'Status': False, 'Errors': 'Неверные данные в элементе'})
                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated}, status=200)
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """
    A class for updating partner information.

    Methods:
    - post: Update the partner information.

    Attributes:
    - None
    """

    def post(self, request, *args, **kwargs):
        """
                Update the partner price list information.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            # Запускаем задачу Celery для загрузки данных
            result = load_data_from_url.delay(url, request.user.id)
            return JsonResponse({'Status': True, 'TaskID': result.id})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerState(APIView):
    """
       A class for managing partner state.

       Methods:
       - get: Retrieve the state of the partner.

       Attributes:
       - None
       """

    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """
               Retrieve the state of the partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the state of the partner.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        """
               Update the state of a partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id
        ).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter'
        ).select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))
        ).distinct()

        # Возвращаем 404, если заказы не найдены
        if not order.exists():
            return JsonResponse({'Status': False, 'Error': 'No orders found'}, status=404)

        # Сериализация данных вручную
        orders_data = []
        for o in order:
            orders_data.append({
                'id': o.id,
                'user_id': o.user.id,
                'total_sum': o.total_sum,
            })

        return JsonResponse(orders_data, safe=False, status=200)


class ContactView(APIView):
    """
       A class for managing contact information.

       Methods:
       - get: Retrieve the contact information of the authenticated user.
       - post: Create a new contact for the authenticated user.
       - put: Update the contact information of the authenticated user.
       - delete: Delete the contact of the authenticated user.

       Attributes:
       - None
       """

    # получить мои контакты
    def get(self, request, *args, **kwargs):
        """
               Retrieve the contact information of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the contact information.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(
            user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    # добавить новый контакт
    def post(self, request, *args, **kwargs):
        """
        Create a new contact for the authenticated user.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'city', 'street', 'phone'}.issubset(request.data):
            # Вместо использования _mutable, просто обновляем request.data
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить контакт
    def delete(self, request, *args, **kwargs):
        """
               Delete the contact of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать контакт
    # редактировать контакт
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # Проверяем, что указан ID контакта
        contact_id = request.data.get('id')
        if not contact_id:
            return JsonResponse({'Status': False, 'Errors': 'Missing required ID'}, status=400)

        # Проверяем, существует ли контакт
        contact = Contact.objects.filter(id=contact_id, user_id=request.user.id).first()
        if not contact:
            return JsonResponse({'Status': False, 'Errors': 'Contact not found'}, status=404)

        # Проверяем, что указаны данные для обновления
        if len(request.data) <= 1:  # Если передан только ID
            return JsonResponse({'Status': False, 'Errors': 'Not all required arguments specified'}, status=400)

        # Обновляем контакт через сериализатор
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors}, status=400)


class OrderView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    Methods:
    - get: Retrieve the details of a specific order.
    - post: Create a new order.
    - put: Update the details of a specific order.
    - delete: Delete a specific order.

    Attributes:
    - None
    """

    # получить мои заказы
    def get(self, request, *args, **kwargs):
        """
               Retrieve the details of user orders.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the order.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        """
        Разместить заказ из корзины.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            # Проверяем, что id является числом
            if not request.data['id'].isdigit():
                return JsonResponse({'Status': False, 'Errors': 'Invalid id format'}, status=400)

            try:
                is_updated = Order.objects.filter(
                    user_id=request.user.id, id=request.data['id']
                ).update(contact_id=request.data['contact'], state='new')
            except IntegrityError as error:
                return JsonResponse({'Status': False, 'Errors': 'Invalid arguments'}, status=400)
            else:
                if is_updated:
                    new_order.send(sender=self.__class__, user_id=request.user.id)
                    return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Missing required arguments'}, status=400)
