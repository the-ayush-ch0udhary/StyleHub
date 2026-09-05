from django.urls import path
from . import views

app_name = 'coupons'

urlpatterns = [
    path('api/apply/', views.api_apply_coupon, name='api_apply'),
    path('api/remove/', views.api_remove_coupon, name='api_remove'),
]
