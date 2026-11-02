from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('shop/', views.shop_view, name='shop'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('search/', views.search_view, name='search'),
    path('outfit-builder/', views.outfit_builder_view, name='outfit_builder'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('api/variant-stock/', views.api_variant_stock, name='api_variant_stock'),
    path('api/pincode-check/', views.api_pincode_check, name='api_pincode_check'),
    path('api/ai-stylist/', views.api_ai_stylist, name='api_ai_stylist'),
    path('newsletter/subscribe/', views.newsletter_subscribe_view, name='newsletter_subscribe'),
]
