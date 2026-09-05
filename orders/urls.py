from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('order/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('order/<str:order_number>/cancel/', views.order_cancel_view, name='order_cancel'),
    path('order/<str:order_number>/invoice/', views.order_invoice_view, name='order_invoice'),
]
