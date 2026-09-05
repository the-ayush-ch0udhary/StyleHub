from .services import CartService

def cart_context(request):
    """Provides cart item count and summary for navbar and mini-bag."""
    try:
        cart = CartService.get_or_create_cart(request)
        item_count = cart.total_items
        cart_subtotal = cart.subtotal
    except Exception:
        cart = None
        item_count = 0
        cart_subtotal = 0

    return {
        'active_cart': cart,
        'cart_item_count': item_count,
        'cart_subtotal': cart_subtotal,
    }
