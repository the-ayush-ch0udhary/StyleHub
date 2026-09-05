import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import UserProfile, Address
from products.models import Category, Product, ProductImage, ProductVariant
from coupons.models import Coupon, CouponUsage
from reviews.models import Review
from orders.models import Order, OrderItem

class Command(BaseCommand):
    help = 'Seeds StyleHub database with comprehensive luxury fashion catalog, users, variants, coupons, and sample orders'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Starting StyleHub database seed...'))

        # 1. Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@stylehub.com',
                'first_name': 'Alexander',
                'last_name': 'Vance',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin1234')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Admin user created: admin / admin1234'))

        # 2. Demo Customer User
        customer, created = User.objects.get_or_create(
            username='john_doe',
            defaults={
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
            }
        )
        if created:
            customer.set_password('password123')
            customer.save()
            customer.profile.phone_number = '+91 9876543210'
            customer.profile.save()

            # Default Address
            Address.objects.create(
                user=customer,
                full_name='John Doe',
                phone='+91 9876543210',
                address_line_1='Flat 402, Signature Heights, MG Road',
                address_line_2='Indiranagar',
                city='Bengaluru',
                state='Karnataka',
                postal_code='560038',
                country='India',
                is_default=True
            )
            self.stdout.write(self.style.SUCCESS('Customer user created: john_doe / password123'))

        # 3. Categories
        categories_data = [
            {'name': "Men's Apparel", 'slug': 'men', 'description': 'Refined masculine tailoring, relaxed shirts, and daily essentials.'},
            {'name': "Women's Collection", 'slug': 'women', 'description': 'Contemporary silhouettes, draped dresses, and luxe knitwear.'},
            {'name': "Jackets & Outerwear", 'slug': 'jackets', 'description': 'Structured trench coats, leather jackets, and insulated bombers.'},
            {'name': "Hoodies & Sweatshirts", 'slug': 'hoodies', 'description': 'Heavyweight 450 GSM French terry hoodies and fleece layers.'},
            {'name': "Denim & Jeans", 'slug': 'denim', 'description': 'Selvedge raw denim, relaxed vintage fits, and sculpted washes.'},
            {'name': "Shirts & Tops", 'slug': 'shirts', 'description': 'Breathable Italian linen, poplin button-downs, and boxy cut tees.'},
            {'name': "Footwear & Sneakers", 'slug': 'footwear', 'description': 'Minimalist calfskin leather sneakers and handcrafted chelsea boots.'},
            {'name': "Accessories", 'slug': 'accessories', 'description': 'Full-grain leather belts, silk scarves, and understated caps.'},
        ]

        categories = {}
        for cat_info in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=cat_info['slug'],
                defaults={'name': cat_info['name'], 'description': cat_info['description'], 'is_active': True}
            )
            categories[cat_info['slug']] = cat

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(categories)} categories."))

        # 4. Products Data
        products_data = [
            {
                'category': 'hoodies',
                'name': 'Oversized Heavyweight French Terry Hoodie',
                'slug': 'oversized-heavyweight-french-terry-hoodie',
                'brand': 'StyleHub Signature',
                'description': 'Engineered from ultra-heavyweight 480 GSM organic cotton French terry. Features dropped shoulders, a double-layered hood without drawstrings for a clean architectural aesthetic, and ribbed hems.',
                'base_price': Decimal('3499.00'),
                'discount_percentage': Decimal('15.00'),
                'is_featured': True,
                'is_bestseller': True,
                'is_new_arrival': True,
                'variants': [
                    {'size': 'S', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-HD-BLK-S', 'stock': 12},
                    {'size': 'M', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-HD-BLK-M', 'stock': 18},
                    {'size': 'L', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-HD-BLK-L', 'stock': 8},
                    {'size': 'XL', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-HD-BLK-XL', 'stock': 4},
                    {'size': 'S', 'color': 'Heather Grey', 'color_code': '#9CA3AF', 'sku': 'SH-HD-GRY-S', 'stock': 10},
                    {'size': 'M', 'color': 'Heather Grey', 'color_code': '#9CA3AF', 'sku': 'SH-HD-GRY-M', 'stock': 15},
                    {'size': 'L', 'color': 'Heather Grey', 'color_code': '#9CA3AF', 'sku': 'SH-HD-GRY-L', 'stock': 6},
                    {'size': 'M', 'color': 'Desert Camel', 'color_code': '#D97706', 'sku': 'SH-HD-CML-M', 'stock': 3}, # Low stock test
                ]
            },
            {
                'category': 'jackets',
                'name': 'Structured Wool-Blend Overcoat',
                'slug': 'structured-wool-blend-overcoat',
                'brand': 'Noir Atelier',
                'description': 'A tailored double-breasted overcoat woven from high-grade wool blend. Features sharp peak lapels, horn buttons, deep flap pockets, and a silk cupro inner lining.',
                'base_price': Decimal('8999.00'),
                'discount_percentage': Decimal('20.00'),
                'is_featured': True,
                'is_bestseller': True,
                'is_new_arrival': False,
                'variants': [
                    {'size': 'M', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-OC-BLK-M', 'stock': 5},
                    {'size': 'L', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-OC-BLK-L', 'stock': 7},
                    {'size': 'M', 'color': 'Midnight Navy', 'color_code': '#1E3A8A', 'sku': 'SH-OC-NVY-M', 'stock': 4},
                    {'size': 'L', 'color': 'Midnight Navy', 'color_code': '#1E3A8A', 'sku': 'SH-OC-NVY-L', 'stock': 6},
                    {'size': 'XL', 'color': 'Camel Tan', 'color_code': '#B45309', 'sku': 'SH-OC-CML-XL', 'stock': 2}, # Low stock
                ]
            },
            {
                'category': 'shirts',
                'name': 'Relaxed Camp-Collar Linen Shirt',
                'slug': 'relaxed-camp-collar-linen-shirt',
                'brand': 'Milano Luxe',
                'description': 'Pure 100% Normandy linen shirt cut in a breezy boxy silhouette. Finished with mother-of-pearl buttons and a clean cuban collar.',
                'base_price': Decimal('2799.00'),
                'discount_percentage': Decimal('10.00'),
                'is_featured': False,
                'is_bestseller': True,
                'is_new_arrival': True,
                'variants': [
                    {'size': 'S', 'color': 'Pure White', 'color_code': '#FFFFFF', 'sku': 'SH-LS-WHT-S', 'stock': 14},
                    {'size': 'M', 'color': 'Pure White', 'color_code': '#FFFFFF', 'sku': 'SH-LS-WHT-M', 'stock': 20},
                    {'size': 'L', 'color': 'Pure White', 'color_code': '#FFFFFF', 'sku': 'SH-LS-WHT-L', 'stock': 12},
                    {'size': 'M', 'color': 'Olive Green', 'color_code': '#15803D', 'sku': 'SH-LS-OLV-M', 'stock': 8},
                    {'size': 'L', 'color': 'Olive Green', 'color_code': '#15803D', 'sku': 'SH-LS-OLV-L', 'stock': 7},
                ]
            },
            {
                'category': 'denim',
                'name': 'Selvedge Straight-Leg Japanese Denim',
                'slug': 'selvedge-straight-leg-japanese-denim',
                'brand': 'Heritage Denim',
                'description': '14oz shuttle-loom Japanese selvedge denim. Raw indigo untreated surface with copper hardware that patinas gracefully with wear.',
                'base_price': Decimal('4999.00'),
                'discount_percentage': Decimal('0.00'),
                'is_featured': True,
                'is_bestseller': False,
                'is_new_arrival': True,
                'variants': [
                    {'size': '30', 'color': 'Raw Indigo', 'color_code': '#1E3A8A', 'sku': 'SH-DN-IND-30', 'stock': 8},
                    {'size': '32', 'color': 'Raw Indigo', 'color_code': '#1E3A8A', 'sku': 'SH-DN-IND-32', 'stock': 15},
                    {'size': '34', 'color': 'Raw Indigo', 'color_code': '#1E3A8A', 'sku': 'SH-DN-IND-34', 'stock': 10},
                    {'size': '32', 'color': 'Washed Charcoal', 'color_code': '#374151', 'sku': 'SH-DN-CHR-32', 'stock': 9},
                ]
            },
            {
                'category': 'men',
                'name': 'Heavy Cotton Boxy Crewneck T-Shirt',
                'slug': 'heavy-cotton-boxy-crewneck-t-shirt',
                'brand': 'StyleHub Signature',
                'description': 'Crafted from 280 GSM combed single jersey cotton with reinforced collar ribbing that retains its structure wash after wash.',
                'base_price': Decimal('1499.00'),
                'discount_percentage': Decimal('20.00'),
                'is_featured': False,
                'is_bestseller': True,
                'is_new_arrival': False,
                'variants': [
                    {'size': 'S', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-TS-BLK-S', 'stock': 25},
                    {'size': 'M', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-TS-BLK-M', 'stock': 30},
                    {'size': 'L', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-TS-BLK-L', 'stock': 20},
                    {'size': 'S', 'color': 'Pure White', 'color_code': '#FFFFFF', 'sku': 'SH-TS-WHT-S', 'stock': 22},
                    {'size': 'M', 'color': 'Pure White', 'color_code': '#FFFFFF', 'sku': 'SH-TS-WHT-M', 'stock': 28},
                    {'size': 'L', 'color': 'Pure White', 'color_code': '#FFFFFF', 'sku': 'SH-TS-WHT-L', 'stock': 18},
                ]
            },
            {
                'category': 'women',
                'name': 'Silk Charmeuse Bias-Cut Slip Dress',
                'slug': 'silk-charmeuse-bias-cut-slip-dress',
                'brand': 'Noir Atelier',
                'description': 'A sensual 100% mulberry silk maxi slip dress cut on the bias for fluid movement. Delicately draped cowl neck and adjustable cross-back straps.',
                'base_price': Decimal('6499.00'),
                'discount_percentage': Decimal('25.00'),
                'is_featured': True,
                'is_bestseller': True,
                'is_new_arrival': True,
                'variants': [
                    {'size': 'XS', 'color': 'Champagne Gold', 'color_code': '#F59E0B', 'sku': 'SH-DR-GLD-XS', 'stock': 6},
                    {'size': 'S', 'color': 'Champagne Gold', 'color_code': '#F59E0B', 'sku': 'SH-DR-GLD-S', 'stock': 9},
                    {'size': 'M', 'color': 'Champagne Gold', 'color_code': '#F59E0B', 'sku': 'SH-DR-GLD-M', 'stock': 7},
                    {'size': 'S', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-DR-BLK-S', 'stock': 11},
                    {'size': 'M', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-DR-BLK-M', 'stock': 8},
                ]
            },
            {
                'category': 'footwear',
                'name': 'Minimalist Calfskin Leather Low-Tops',
                'slug': 'minimalist-calfskin-leather-low-tops',
                'brand': 'UrbanCraft',
                'description': 'Handcrafted in full-grain Italian calfskin with Margom rubber cupsole and waxed cotton laces. Includes memory foam insole.',
                'base_price': Decimal('7499.00'),
                'discount_percentage': Decimal('15.00'),
                'is_featured': True,
                'is_bestseller': False,
                'is_new_arrival': True,
                'variants': [
                    {'size': 'UK 7', 'color': 'Monochrome White', 'color_code': '#FFFFFF', 'sku': 'SH-SN-WHT-7', 'stock': 5},
                    {'size': 'UK 8', 'color': 'Monochrome White', 'color_code': '#FFFFFF', 'sku': 'SH-SN-WHT-8', 'stock': 8},
                    {'size': 'UK 9', 'color': 'Monochrome White', 'color_code': '#FFFFFF', 'sku': 'SH-SN-WHT-9', 'stock': 10},
                    {'size': 'UK 10', 'color': 'Monochrome White', 'color_code': '#FFFFFF', 'sku': 'SH-SN-WHT-10', 'stock': 6},
                ]
            },
            {
                'category': 'accessories',
                'name': 'Full-Grain Bridle Leather Minimalist Belt',
                'slug': 'full-grain-bridle-leather-minimalist-belt',
                'brand': 'UrbanCraft',
                'description': 'Hand-burnished 3.5mm thick vegetable-tanned bridle leather belt with solid brass matte gunmetal buckle.',
                'base_price': Decimal('1899.00'),
                'discount_percentage': Decimal('0.00'),
                'is_featured': False,
                'is_bestseller': False,
                'is_new_arrival': True,
                'variants': [
                    {'size': 'Free Size', 'color': 'Rich Cognac Brown', 'color_code': '#78350F', 'sku': 'SH-BLT-BRN-FS', 'stock': 15},
                    {'size': 'Free Size', 'color': 'Obsidian Black', 'color_code': '#111827', 'sku': 'SH-BLT-BLK-FS', 'stock': 20},
                ]
            }
        ]

        for p_data in products_data:
            cat = categories[p_data['category']]
            prod, _ = Product.objects.get_or_create(
                slug=p_data['slug'],
                defaults={
                    'category': cat,
                    'name': p_data['name'],
                    'brand': p_data['brand'],
                    'description': p_data['description'],
                    'base_price': p_data['base_price'],
                    'discount_percentage': p_data['discount_percentage'],
                    'is_featured': p_data['is_featured'],
                    'is_bestseller': p_data['is_bestseller'],
                    'is_new_arrival': p_data['is_new_arrival'],
                    'is_active': True,
                }
            )

            # Create Variants
            for v_data in p_data['variants']:
                ProductVariant.objects.get_or_create(
                    product=prod,
                    size=v_data['size'],
                    color=v_data['color'],
                    defaults={
                        'color_code': v_data['color_code'],
                        'sku': v_data['sku'],
                        'stock_quantity': v_data['stock'],
                        'is_active': True,
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(products_data)} products with complete variant matrices."))

        # 5. Active Discount Coupons
        now = timezone.now()
        coupons_data = [
            {
                'code': 'WELCOME10',
                'discount_type': 'PERCENTAGE',
                'discount_value': Decimal('10.00'),
                'minimum_order_amount': Decimal('1000.00'),
                'maximum_discount': Decimal('500.00'),
                'valid_until': now + timezone.timedelta(days=365),
                'usage_limit': 500,
            },
            {
                'code': 'STYLE500',
                'discount_type': 'FIXED',
                'discount_value': Decimal('500.00'),
                'minimum_order_amount': Decimal('2500.00'),
                'maximum_discount': None,
                'valid_until': now + timezone.timedelta(days=180),
                'usage_limit': 200,
            },
            {
                'code': 'FASHION20',
                'discount_type': 'PERCENTAGE',
                'discount_value': Decimal('20.00'),
                'minimum_order_amount': Decimal('3000.00'),
                'maximum_discount': Decimal('1000.00'),
                'valid_until': now + timezone.timedelta(days=90),
                'usage_limit': 100,
            },
        ]

        for c_info in coupons_data:
            Coupon.objects.get_or_create(
                code=c_info['code'],
                defaults={
                    'discount_type': c_info['discount_type'],
                    'discount_value': c_info['discount_value'],
                    'minimum_order_amount': c_info['minimum_order_amount'],
                    'maximum_discount': c_info['maximum_discount'],
                    'valid_from': now - timezone.timedelta(days=5),
                    'valid_until': c_info['valid_until'],
                    'usage_limit': c_info['usage_limit'],
                    'is_active': True,
                }
            )

        self.stdout.write(self.style.SUCCESS("Loaded active coupons (WELCOME10, STYLE500, FASHION20)."))

        # 6. Sample Verified Reviews
        p_hoodie = Product.objects.get(slug='oversized-heavyweight-french-terry-hoodie')
        Review.objects.get_or_create(
            user=customer,
            product=p_hoodie,
            defaults={
                'rating': 5,
                'title': 'Best heavyweight hoodie on the market',
                'comment': 'The 480 GSM fabric weight is phenomenal. The double-lined hood holds its shape perfectly without slouching. Highly recommend sizing true to size for a relaxed drape.',
                'is_verified_purchase': True
            }
        )

        p_coat = Product.objects.get(slug='structured-wool-blend-overcoat')
        Review.objects.get_or_create(
            user=customer,
            product=p_coat,
            defaults={
                'rating': 5,
                'title': 'Sublime luxury tailoring',
                'comment': 'Looks like a ₹25,000 Italian designer coat. High shoulder structure and the peak lapels give an incredible commanding silhouette.',
                'is_verified_purchase': True
            }
        )

        # 7. Sample Orders for Dashboard Analytics
        order1, created = Order.objects.get_or_create(
            order_number='SH-DEMO-001',
            defaults={
                'user': customer,
                'shipping_full_name': 'John Doe',
                'shipping_phone': '+91 9876543210',
                'shipping_address_line_1': 'Flat 402, Signature Heights',
                'shipping_city': 'Bengaluru',
                'shipping_state': 'Karnataka',
                'shipping_postal_code': '560038',
                'shipping_country': 'India',
                'subtotal': Decimal('6998.00'),
                'discount': Decimal('500.00'),
                'shipping_charge': Decimal('0.00'),
                'tax': Decimal('324.90'),
                'total_amount': Decimal('6822.90'),
                'coupon_code': 'STYLE500',
                'status': 'DELIVERED',
                'payment_status': 'PAID',
                'payment_method': 'RAZORPAY',
                'razorpay_payment_id': 'pay_demo_8829102',
                'tracking_number': 'BLR-EXP-99218',
            }
        )
        if created:
            v1 = p_hoodie.variants.first()
            OrderItem.objects.create(
                order=order1,
                variant=v1,
                product_name=p_hoodie.name,
                sku=v1.sku,
                size=v1.size,
                color=v1.color,
                quantity=2,
                unit_price=v1.current_price,
                subtotal=v1.current_price * 2
            )

        order2, created = Order.objects.get_or_create(
            order_number='SH-DEMO-002',
            defaults={
                'user': customer,
                'shipping_full_name': 'John Doe',
                'shipping_phone': '+91 9876543210',
                'shipping_address_line_1': 'Flat 402, Signature Heights',
                'shipping_city': 'Bengaluru',
                'shipping_state': 'Karnataka',
                'shipping_postal_code': '560038',
                'shipping_country': 'India',
                'subtotal': Decimal('7199.20'),
                'discount': Decimal('0.00'),
                'shipping_charge': Decimal('0.00'),
                'tax': Decimal('359.96'),
                'total_amount': Decimal('7559.16'),
                'status': 'PROCESSING',
                'payment_status': 'PAID',
                'payment_method': 'RAZORPAY',
                'razorpay_payment_id': 'pay_demo_992144',
                'tracking_number': 'BLR-EXP-11029',
            }
        )
        if created:
            v2 = p_coat.variants.first()
            OrderItem.objects.create(
                order=order2,
                variant=v2,
                product_name=p_coat.name,
                sku=v2.sku,
                size=v2.size,
                color=v2.color,
                quantity=1,
                unit_price=v2.current_price,
                subtotal=v2.current_price
            )

        self.stdout.write(self.style.SUCCESS('StyleHub sample data seeded successfully! Ready for production showcase.'))
