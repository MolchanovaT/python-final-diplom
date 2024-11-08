from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken
from django.shortcuts import render

from backend.models import TaskStatus, Shop
from backend.tasks import load_data_from_url

from reference.netology_pd_diplom.backend import forms


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


# Создаем форму для указания URL, чтобы запускать задачу с URL, указанным администратором.
class LoadDataForm(forms.Form):
    url = forms.URLField(label='URL для загрузки данных', required=True)


# Добавляем в модель Admin для Shop новую функцию start_load_data_task
@admin.action(description="Запустить задачу загрузки данных для выбранных магазинов")
def start_load_data_task(self, request, queryset):
    form = LoadDataForm(request.POST or None)

    if 'apply' in request.POST:  # Обработка отправки формы
        if form.is_valid():
            url = form.cleaned_data['url']
            for shop in queryset:
                task = load_data_from_url.apply_async(args=[url, shop.user_id])

                # Создание записи TaskStatus для отслеживания выполнения задачи
                TaskStatus.objects.create(
                    user=shop.user,
                    task_id=task.id,
                    status='PENDING'
                )
            self.message_user(request, "Задача загружена в очередь")
            return None

    # Если форма еще не отправлена, показать ее в админке
    return render(request, 'admin/run_task_form.html', {'form': form, 'shops': queryset})


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    actions = [start_load_data_task]


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
