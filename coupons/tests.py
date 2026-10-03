from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from coupons.models import Coupon, CouponUsage
from orders.models import Order
from products.models import Category, Product, ProductVariant

class CouponTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='couponuser', password='Password123!')
        self.category = Category.objects.create(name='Apparel', slug='apparel')
        self.product = Product.objects.create(
            category=self.category,
            name='Luxury Tee',
            slug='luxury-tee',
            base_price=Decimal('1000.00'),
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='White',
            sku='SH-LUX-WHT-M',
            stock_quantity=10,
            is_active=True
        )
        self.coupon = Coupon.objects.create(
            code='SAVE20',
            discount_type='PERCENTAGE',
            discount_value=Decimal('20.00'),
            minimum_order_amount=Decimal('500.00'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
            usage_limit=10,
            per_user_limit=1,
            is_active=True
        )

    def test_coupon_discount_calculation(self):
        self.assertEqual(self.coupon.calculate_discount(Decimal('1000.00')), Decimal('200.00'))
        self.assertEqual(self.coupon.calculate_discount(Decimal('400.00')), Decimal('0.00'))

    def test_coupon_api_application(self):
        self.client.login(username='couponuser', password='Password123!')
        # Add item to cart
        self.client.post(reverse('cart:api_add'), {'variant_id': self.variant.id, 'quantity': 1})

        # Apply coupon
        resp = self.client.post(reverse('coupons:api_apply'), {'coupon_code': 'SAVE20'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['discount'], 200.0)

    def test_coupon_per_user_limit_enforcement(self):
        order = Order.objects.create(
            user=self.user,
            shipping_full_name='Test',
            shipping_phone='1234567890',
            shipping_address_line_1='Street',
            shipping_city='City',
            shipping_state='State',
            shipping_postal_code='123456',
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('800.00'),
        )
        CouponUsage.objects.create(coupon=self.coupon, user=self.user, order=order)

        valid, msg = self.coupon.is_valid_for_user(self.user, Decimal('1000.00'))
        self.assertFalse(valid)
        self.assertIn('maximum allowed 1 time', msg)
