from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_view, name='wishlist_view'),
    path('toggle/<int:product_id>/', views.api_toggle_wishlist, name='toggle_wishlist'),
    path('move-to-cart/<int:item_id>/', views.move_to_cart_view, name='move_to_cart'),
]
