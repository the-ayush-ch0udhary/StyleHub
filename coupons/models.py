from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage Discount (%)'),
        ('FIXED', 'Fixed Amount Discount (₹)'),
    ]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Percentage or Fixed Amount")
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Caps percentage discount")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=100, help_text="Total number of times this coupon can be used")
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.discount_type == 'PERCENTAGE':
            return f"{self.code} ({int(self.discount_value)}% OFF)"
        return f"{self.code} (₹{self.discount_value} OFF)"

    def is_valid_now(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_until and self.used_count < self.usage_limit

    def is_valid_for_cart(self, subtotal):
        if not self.is_valid_now():
            return False
        return subtotal >= self.minimum_order_amount

    def calculate_discount(self, subtotal):
        if not self.is_valid_for_cart(subtotal):
            return Decimal('0.00')

        if self.discount_type == 'PERCENTAGE':
            raw_discount = (subtotal * self.discount_value) / Decimal('100.0')
            if self.maximum_discount and self.maximum_discount > 0:
                discount = min(raw_discount, self.maximum_discount)
            else:
                discount = raw_discount
        else:
            discount = min(self.discount_value, subtotal)

        return round(discount, 2)

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='coupon_usages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"
