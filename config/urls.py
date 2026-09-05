from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

# Custom Error Views
def custom_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def custom_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def custom_500(request):
    return render(request, 'errors/500.html', status=500)

handler404 = 'config.urls.custom_404'
handler403 = 'config.urls.custom_403'
handler500 = 'config.urls.custom_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('wishlist/', include('wishlist.urls', namespace='wishlist')),
    path('reviews/', include('reviews.urls', namespace='reviews')),
    path('coupons/', include('coupons.urls', namespace='coupons')),
    path('', include('products.urls', namespace='products')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
