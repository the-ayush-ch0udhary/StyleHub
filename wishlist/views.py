from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import WishlistItem
from products.models import Product
from cart.services import CartService

@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product', 'product__category').prefetch_related('product__images', 'product__variants')
    return render(request, 'wishlist/wishlist.html', {'wishlist_items': items})

@login_required
@require_POST
def api_toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    wishlist_item = WishlistItem.objects.filter(user=request.user, product=product).first()

    if wishlist_item:
        wishlist_item.delete()
        added = False
        message = f"Removed '{product.name}' from your wishlist."
    else:
        WishlistItem.objects.create(user=request.user, product=product)
        added = True
        message = f"Added '{product.name}' to your wishlist."

    count = WishlistItem.objects.filter(user=request.user).count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'added': added,
            'wishlist_count': count,
            'message': message,
        })

    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))

@login_required
@require_POST
def move_to_cart_view(request, item_id):
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, user=request.user)
    product = wishlist_item.product

    # Check for in-stock variant
    available_variant = product.variants.filter(is_active=True, stock_quantity__gt=0).first()
    if not available_variant:
        messages.error(request, f"Sorry, '{product.name}' is currently out of stock.")
        return redirect('wishlist:wishlist_view')

    cart = CartService.get_or_create_cart(request)
    success, message = CartService.add_to_cart(cart, available_variant.id, 1)

    if success:
        wishlist_item.delete()
        messages.success(request, f"Moved '{product.name}' ({available_variant.color}, {available_variant.size}) to your bag.")
    else:
        messages.error(request, message)

    return redirect('wishlist:wishlist_view')
