from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage, ProductVariant

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'preview')
    readonly_fields = ('preview',)

    def preview(self, instance):
        if instance.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 4px;" />', instance.image.url)
        return "-"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'color_code', 'sku', 'price', 'stock_quantity', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'base_price', 'discount_percentage', 'discounted_price_display', 'total_stock', 'is_active', 'is_featured', 'is_bestseller', 'is_new_arrival')
    list_filter = ('is_active', 'is_featured', 'is_bestseller', 'is_new_arrival', 'category', 'brand')
    search_fields = ('name', 'brand', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ['make_featured', 'make_active', 'make_inactive']

    def discounted_price_display(self, obj):
        return f"₹{obj.discounted_price}"
    discounted_price_display.short_description = 'Sale Price'

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
    make_featured.short_description = "Mark selected products as Featured"

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = "Mark selected products as Active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = "Mark selected products as Inactive"

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product', 'color', 'size', 'stock_quantity', 'current_price', 'is_active')
    list_filter = ('size', 'color', 'is_active', 'product__category')
    search_fields = ('sku', 'product__name', 'color')
    list_editable = ('stock_quantity', 'is_active')
