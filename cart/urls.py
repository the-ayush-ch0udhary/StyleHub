from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail_view, name='cart_detail'),
    path('api/add/', views.api_add_to_cart, name='api_add'),
    path('api/update/', views.api_update_cart, name='api_update'),
    path('api/remove/', views.api_remove_cart, name='api_remove'),
    path('api/clear/', views.api_clear_cart, name='api_clear'),
    path('api/drawer/', views.api_cart_drawer, name='api_drawer'),
    path('api/bundle/', views.api_add_bundle, name='api_bundle'),
]
