from django.db import models
from django.contrib.auth.models import User
from products.models import ProductVariant
from decimal import Decimal

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Guest Cart ({self.session_key})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        total = Decimal('0.00')
        for item in self.items.select_related('variant', 'variant__product'):
            total += item.total_price
        return round(total, 2)

    @property
    def total_original_price(self):
        total = Decimal('0.00')
        for item in self.items.select_related('variant', 'variant__product'):
            total += (item.variant.product.base_price * item.quantity)
        return round(total, 2)

    @property
    def total_savings(self):
        return round(max(Decimal('0.00'), self.total_original_price - self.subtotal), 2)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'variant')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.quantity}x {self.variant}"

    @property
    def unit_price(self):
        return self.variant.current_price

    @property
    def total_price(self):
        return round(self.unit_price * self.quantity, 2)

    @property
    def is_available(self):
        return self.variant.is_active and self.variant.stock_quantity >= self.quantity
