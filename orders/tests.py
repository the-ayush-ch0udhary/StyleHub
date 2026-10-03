from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from products.models import Category, Product, ProductVariant
from orders.models import Order, OrderItem

class OrderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='orderuser', password='Password123!')
        self.category = Category.objects.create(name='Shirts', slug='shirts')
        self.product = Product.objects.create(
            category=self.category,
            name='Oxford Shirt',
            slug='oxford-shirt',
            base_price=Decimal('2500.00'),
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='L',
            color='Sky Blue',
            sku='SH-OXF-BLU-L',
            stock_quantity=10,
            is_active=True
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_full_name='Test Buyer',
            shipping_phone='9876543210',
            shipping_address_line_1='100 Marine Drive',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_postal_code='400020',
            shipping_country='India',
            subtotal=Decimal('2500.00'),
            total_amount=Decimal('2500.00'),
            status='CONFIRMED',
            payment_status='PAID',
            payment_method='COD',
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name=self.product.name,
            sku=self.variant.sku,
            size=self.variant.size,
            color=self.variant.color,
            quantity=2,
            unit_price=Decimal('1250.00'),
            subtotal=Decimal('2500.00'),
        )
        # Deduct stock as would happen on order creation
        self.variant.stock_quantity = 8
        self.variant.save()

    def test_order_number_generation(self):
        self.assertTrue(self.order.order_number.startswith('SH-'))
        self.assertTrue(self.order.is_cancellable)

    def test_order_cancellation_restores_inventory(self):
        self.client.login(username='orderuser', password='Password123!')
        url = reverse('orders:order_cancel', kwargs={'order_number': self.order.order_number})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'CANCELLED')
        self.assertEqual(self.order.payment_status, 'REFUNDED')

        # Stock should be restored from 8 back to 10
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 10)

    def test_order_invoice_renders(self):
        self.client.login(username='orderuser', password='Password123!')
        url = reverse('orders:order_invoice', kwargs={'order_number': self.order.order_number})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.order.order_number)
        self.assertContains(resp, 'Oxford Shirt')
