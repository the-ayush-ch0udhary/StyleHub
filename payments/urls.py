from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('verify/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('cod-place-order/', views.cod_place_order, name='cod_place_order'),
    path('success/<str:order_number>/', views.payment_success_view, name='payment_success'),
    path('failed/', views.payment_failed_view, name='payment_failed'),
]
