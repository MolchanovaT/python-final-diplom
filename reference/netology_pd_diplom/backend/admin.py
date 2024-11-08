from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken

from django.utils.html import format_html
from celery.result import AsyncResult
from backend.models import TaskStatus, Shop
from backend.tasks import load_data_from_url


@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'created_at', 'updated_at')
    readonly_fields = ('task_id', 'status', 'user', 'created_at', 'updated_at')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'run_task', 'check_task_status')

    actions = ['start_load_data_task']

    def start_load_data_task(self, request, queryset):
        for shop in queryset:
            # URL для загрузки данных можно хранить в модели Shop или получать из другого источника
            url = shop.data_url  # Предполагаем, что у модели есть поле `data_url`
            task = load_data_from_url.apply_async(args=[url, shop.user_id])

            # Создание записи TaskStatus для отслеживания статуса
            TaskStatus.objects.create(
                user=shop.user,
                task_id=task.id,
                status='PENDING'
            )
        self.message_user(request, "Задача загружена в очередь")

    start_load_data_task.short_description = 'Запустить задачу загрузки данных'

    def run_task(self, obj):
        """Создание кнопки для запуска задачи"""
        return format_html(
            '<a class="button" href="{}">Запустить задачу</a>',
            f'/admin/run_task/{obj.id}/'
        )

    def check_task_status(self, obj):
        """Показать статус задачи"""
        task = TaskStatus.objects.filter(user=obj.user).order_by('-created_at').first()
        if task:
            return format_html('<span>{}</span>', task.status)
        return "Нет задачи"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    pass


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    pass


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    pass


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    pass


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    pass


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    pass


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at',)
