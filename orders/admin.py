from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'sku', 'size', 'color', 'quantity', 'unit_price', 'subtotal')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'status', 'payment_status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'shipping_phone', 'razorpay_order_id')
    readonly_fields = ('order_number', 'subtotal', 'discount', 'shipping_charge', 'tax', 'total_amount', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    actions = ['mark_confirmed', 'mark_processing', 'mark_shipped', 'mark_delivered', 'mark_cancelled']

    def mark_confirmed(self, request, queryset):
        queryset.update(status='CONFIRMED')
    mark_confirmed.short_description = "Mark selected orders as Confirmed"

    def mark_processing(self, request, queryset):
        queryset.update(status='PROCESSING')
    mark_processing.short_description = "Mark selected orders as Processing"

    def mark_shipped(self, request, queryset):
        queryset.update(status='SHIPPED')
    mark_shipped.short_description = "Mark selected orders as Shipped"

    def mark_delivered(self, request, queryset):
        queryset.update(status='DELIVERED')
    mark_delivered.short_description = "Mark selected orders as Delivered"

    def mark_cancelled(self, request, queryset):
        for order in queryset:
            if order.is_cancellable:
                for item in order.items.select_related('variant'):
                    if item.variant:
                        item.variant.stock_quantity += item.quantity
                        item.variant.save()
                order.status = 'CANCELLED'
                order.save()
    mark_cancelled.short_description = "Cancel selected orders & restore stock"
