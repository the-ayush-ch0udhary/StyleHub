from decimal import Decimal
import json
import hmac
import hashlib
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Address
from products.models import Category, Product, ProductVariant
from orders.models import Order
from cart.services import CartService

class PaymentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='payuser', password='Password123!')
        self.category = Category.objects.create(name='Denim', slug='denim')
        self.product = Product.objects.create(
            category=self.category,
            name='Slim Jeans',
            slug='slim-jeans',
            base_price=Decimal('3000.00'),
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='32',
            color='Indigo',
            sku='SH-JNS-IND-32',
            stock_quantity=5,
            is_active=True
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name='Pay Customer',
            phone='9876543210',
            address_line_1='456 High Street',
            city='Bengaluru',
            state='Karnataka',
            postal_code='560001',
            country='India',
            is_default=True
        )

    def test_cod_order_placement(self):
        self.client.login(username='payuser', password='Password123!')
        self.client.post(reverse('cart:api_add'), {'variant_id': self.variant.id, 'quantity': 2})

        resp = self.client.post(reverse('payments:cod_place_order'), {
            'address_id': self.address.id
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])

        # Variant stock should have decreased from 5 to 3
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 3)

        # Order created
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment_method, 'COD')
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.items.count(), 1)

    @override_settings(RAZORPAY_WEBHOOK_SECRET='test_webhook_secret_123')
    def test_razorpay_webhook_signature_verification(self):
        order = Order.objects.create(
            user=self.user,
            shipping_full_name='Test',
            shipping_phone='1234567890',
            shipping_address_line_1='Street',
            shipping_city='City',
            shipping_state='State',
            shipping_postal_code='123456',
            subtotal=Decimal('3000.00'),
            total_amount=Decimal('3000.00'),
            razorpay_order_id='order_test_rzp_123',
            status='PENDING',
            payment_status='PENDING',
        )

        payload = {
            'event': 'order.paid',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test_456',
                        'order_id': 'order_test_rzp_123',
                        'status': 'captured'
                    }
                }
            }
        }
        body = json.dumps(payload)
        secret = 'test_webhook_secret_123'
        signature = hmac.new(secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).hexdigest()

        resp = self.client.post(
            reverse('payments:razorpay_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature
        )
        self.assertEqual(resp.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.payment_status, 'PAID')
        self.assertEqual(order.razorpay_payment_id, 'pay_test_456')
