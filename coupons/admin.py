from django.contrib import admin
from .models import Coupon, CouponUsage

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'minimum_order_amount', 'maximum_discount', 'valid_from', 'valid_until', 'usage_limit', 'used_count', 'is_active')
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_until')
    search_fields = ('code',)
    readonly_fields = ('used_count', 'created_at')

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'order', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('coupon__code', 'user__username', 'order__order_number')
