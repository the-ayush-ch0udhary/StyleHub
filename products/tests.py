from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from products.models import Category, Product, ProductVariant

class ProductTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Outerwear', slug='outerwear')
        self.product = Product.objects.create(
            category=self.category,
            name='Tailored Blazer',
            slug='tailored-blazer',
            brand='StyleHub Signature',
            description='Handmade Italian wool blazer.',
            base_price=Decimal('5000.00'),
            discount_percentage=Decimal('20.00'),
            is_active=True,
            is_featured=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Obsidian Black',
            color_code='#111827',
            sku='SH-BLZ-BLK-M',
            stock_quantity=10,
            is_active=True
        )

    def test_product_price_discount(self):
        self.assertEqual(self.product.discounted_price, Decimal('4000.00'))
        self.assertEqual(self.product.savings_amount, Decimal('1000.00'))
        self.assertEqual(self.variant.current_price, Decimal('4000.00'))
        self.assertTrue(self.variant.is_in_stock)

    def test_variant_api_stock_endpoint(self):
        url = reverse('products:api_variant_stock')
        resp = self.client.get(f"{url}?product_id={self.product.id}&color=Obsidian Black&size=M")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sku'], 'SH-BLZ-BLK-M')
        self.assertEqual(data['stock_quantity'], 10)
        self.assertTrue(data['in_stock'])

    def test_shop_filters_and_search(self):
        # Test Category filter
        resp = self.client.get(f"{reverse('products:shop')}?category=outerwear")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tailored Blazer')

        # Test Search query
        search_resp = self.client.get(f"{reverse('products:search')}?q=Blazer")
        self.assertEqual(search_resp.status_code, 200)
        self.assertContains(search_resp, 'Tailored Blazer')
