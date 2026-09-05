from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from products.models import Category, Product, ProductVariant
from cart.models import Cart, CartItem
from cart.services import CartService

class CartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cartuser', password='password123')
        self.category = Category.objects.create(name='Tees', slug='tees')
        self.product = Product.objects.create(
            category=self.category,
            name='Classic Tee',
            slug='classic-tee',
            base_price=Decimal('1000.00'),
            discount_percentage=Decimal('10.00')
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='L',
            color='White',
            sku='TEE-WHT-L',
            stock_quantity=5,
            is_active=True
        )

    def test_add_to_cart_and_stock_limit(self):
        cart = Cart.objects.create(user=self.user)
        
        # Add 3 units
        success, msg = CartService.add_to_cart(cart, self.variant.id, 3)
        self.assertTrue(success)
        self.assertEqual(cart.total_items, 3)
        self.assertEqual(cart.subtotal, Decimal('2700.00'))

        # Add 3 more units (exceeds stock of 5)
        success, msg = CartService.add_to_cart(cart, self.variant.id, 3)
        self.assertTrue(success)
        self.assertEqual(cart.total_items, 5) # Capped at max stock 5

        # Attempt to add another unit when at max stock
        success, msg = CartService.add_to_cart(cart, self.variant.id, 1)
        self.assertFalse(success)
        self.assertIn('already have all 5 available', msg)

    def test_guest_cart_merge_on_login(self):
        # 1. Add item as guest session
        guest_cart = Cart.objects.create(session_key='guest_session_123')
        CartService.add_to_cart(guest_cart, self.variant.id, 2)
        self.assertEqual(guest_cart.total_items, 2)

        # 2. Merge on login
        CartService.merge_guest_cart('guest_session_123', self.user)

        user_cart = Cart.objects.get(user=self.user)
        self.assertEqual(user_cart.total_items, 2)
        self.assertFalse(Cart.objects.filter(session_key='guest_session_123').exists())
