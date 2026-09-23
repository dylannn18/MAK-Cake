from django.contrib import admin

from .models import Bill, Cake, Customer, Inventory, Order, OrderItem, SaleRecord


@admin.register(Cake)
class CakeAdmin(admin.ModelAdmin):
    list_display = ("name", "flavor", "unit_price", "is_active", "updated_at")
    list_filter = ("is_active", "flavor")
    search_fields = ("name", "flavor")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("cake", "quantity_available", "reorder_level", "needs_restock")
    list_filter = ("reorder_level",)
    search_fields = ("cake__name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "order_date", "delivery_date", "total_amount")
    list_filter = ("status", "order_date")
    search_fields = ("customer__full_name", "customer__phone")
    inlines = [OrderItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email", "created_at")
    search_fields = ("full_name", "phone", "email")


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "order", "payment_status", "issued_at", "due_date")
    list_filter = ("payment_status",)
    search_fields = ("bill_number", "order__id", "order__customer__full_name")


@admin.register(SaleRecord)
class SaleRecordAdmin(admin.ModelAdmin):
    list_display = ("order", "payment_method", "amount_received", "sold_at")
    list_filter = ("payment_method",)
    search_fields = ("order__id", "order__customer__full_name")
