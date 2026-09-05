from .models import WishlistItem

def wishlist_context(request):
    """Provides wishlist count and wishlisted product IDs for instantaneous heart styling."""
    if request.user.is_authenticated:
        items = WishlistItem.objects.filter(user=request.user)
        count = items.count()
        wishlist_product_ids = set(items.values_list('product_id', flat=True))
    else:
        count = 0
        wishlist_product_ids = set()

    return {
        'wishlist_count': count,
        'user_wishlist_ids': wishlist_product_ids,
    }
