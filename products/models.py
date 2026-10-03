from django.db import models
from django.utils.text import slugify
from django.db.models import Avg, Count
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete('nav_active_categories')

    def delete(self, *args, **kwargs):
        from django.core.cache import cache
        cache.delete('nav_active_categories')
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def product_count(self):
        return self.products.filter(is_active=True).count()

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    brand = models.CharField(max_length=100, default='StyleHub Signature')
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['is_active', 'base_price']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['is_active', 'is_bestseller']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.brand}-{self.name}")
            slug = base
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand} {self.name}"

    @property
    def discounted_price(self):
        if self.discount_percentage > 0:
            discount = (self.base_price * self.discount_percentage) / Decimal('100.0')
            return round(self.base_price - discount, 2)
        return self.base_price

    @property
    def savings_amount(self):
        return round(self.base_price - self.discounted_price, 2)

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img

    @property
    def total_stock(self):
        return sum(v.stock_quantity for v in self.variants.filter(is_active=True))

    @property
    def in_stock(self):
        return self.total_stock > 0

    @property
    def average_rating(self):
        result = self.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(result, 1) if result else 0.0

    @property
    def review_count(self):
        return self.reviews.count()

    def get_rating_distribution(self):
        total = self.review_count
        dist = {5: 0, 4: 0, 3: 0, 2: 1, 1: 0} if False else {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        counts = self.reviews.values('rating').annotate(c=Count('id'))
        for item in counts:
            dist[item['rating']] = item['c']
        distribution_with_pct = {}
        for star in [5, 4, 3, 2, 1]:
            count = dist.get(star, 0)
            pct = int((count / total * 100)) if total > 0 else 0
            distribution_with_pct[star] = {'count': count, 'percent': pct}
        return distribution_with_pct

    def get_available_sizes(self):
        return list(self.variants.filter(is_active=True).values_list('size', flat=True).distinct())

    def get_available_colors(self):
        colors = []
        seen = set()
        for variant in self.variants.filter(is_active=True):
            if variant.color not in seen:
                seen.add(variant.color)
                colors.append({
                    'name': variant.color,
                    'code': variant.color_code or '#222222',
                })
        return colors

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'id']

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        elif not ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).exists():
            self.is_primary = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small (XS)'),
        ('S', 'Small (S)'),
        ('M', 'Medium (M)'),
        ('L', 'Large (L)'),
        ('XL', 'Extra Large (XL)'),
        ('XXL', '2X Large (XXL)'),
        ('3XL', '3X Large (3XL)'),
        ('28', '28 (Waist)'),
        ('30', '30 (Waist)'),
        ('32', '32 (Waist)'),
        ('34', '34 (Waist)'),
        ('36', '36 (Waist)'),
        ('UK 6', 'UK 6 (Footwear)'),
        ('UK 7', 'UK 7 (Footwear)'),
        ('UK 8', 'UK 8 (Footwear)'),
        ('UK 9', 'UK 9 (Footwear)'),
        ('UK 10', 'UK 10 (Footwear)'),
        ('UK 11', 'UK 11 (Footwear)'),
        ('Free Size', 'Free Size / One Size'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=20, choices=SIZE_CHOICES)
    color = models.CharField(max_length=50)
    color_code = models.CharField(max_length=10, default='#000000', help_text="Hex color code e.g. #000000")
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Leave blank to use product discounted price")
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'size', 'color')
        ordering = ['size', 'color']

    def __str__(self):
        return f"{self.product.name} - {self.color} / {self.size} (SKU: {self.sku})"

    @property
    def current_price(self):
        base_price = self.price if self.price is not None and self.price > 0 else self.product.base_price

        if self.product.discount_percentage > 0:
            discount = (base_price * self.product.discount_percentage) / Decimal('100.0')
            return round(base_price - discount, 2)

        return base_price

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0 and self.is_active
