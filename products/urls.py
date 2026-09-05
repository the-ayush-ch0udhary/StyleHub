from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('shop/', views.shop_view, name='shop'),
    path('search/', views.search_view, name='search'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('api/variant-stock/', views.api_variant_stock, name='api_variant_stock'),
    path('newsletter/subscribe/', views.newsletter_subscribe_view, name='newsletter_subscribe'),
]
