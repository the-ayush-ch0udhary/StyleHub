from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Cart, CartItem
from products.models import ProductVariant

class CartService:
    @staticmethod
    def get_or_create_cart(request):
        """Retrieves or creates the user cart or guest session cart."""
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart

        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return cart

    @staticmethod
    def add_to_cart(cart, variant_id, quantity=1):
        """Adds a variant to cart with strict stock availability checks."""
        try:
            variant = ProductVariant.objects.select_related('product').get(id=variant_id, is_active=True)
        except ProductVariant.DoesNotExist:
            return False, "Selected product variant was not found or is unavailable."

        if not variant.is_in_stock:
            return False, "This product variant is currently out of stock."

        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={'quantity': 0})
        new_quantity = cart_item.quantity + int(quantity)

        if new_quantity > variant.stock_quantity:
            allowed_additional = max(0, variant.stock_quantity - cart_item.quantity)
            if allowed_additional > 0:
                cart_item.quantity = variant.stock_quantity
                cart_item.save()
                return True, f"Only {variant.stock_quantity} units available. Cart updated to maximum available quantity."
            return False, f"Cannot add more units. You already have all {variant.stock_quantity} available items in your cart."

        cart_item.quantity = new_quantity
        cart_item.save()
        return True, f"Added {variant.product.name} ({variant.color}, {variant.size}) to your bag."

    @staticmethod
    def update_cart_item(cart, item_id, quantity):
        """Updates item quantity in cart with inventory check."""
        try:
            item = CartItem.objects.select_related('variant').get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return False, "Item not found in cart."

        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
            return True, "Item removed from cart."

        if quantity > item.variant.stock_quantity:
            item.quantity = item.variant.stock_quantity
            item.save()
            return False, f"Only {item.variant.stock_quantity} units in stock. Adjusted to available maximum."

        item.quantity = quantity
        item.save()
        return True, "Cart updated."

    @staticmethod
    def remove_from_cart(cart, item_id):
        """Removes an item from cart."""
        CartItem.objects.filter(id=item_id, cart=cart).delete()
        return True, "Item removed from bag."

    @staticmethod
    def clear_cart(cart):
        """Empties the cart."""
        cart.items.all().delete()
        return True

    @staticmethod
    @transaction.atomic
    def merge_guest_cart(session_key, user):
        """Merges items from guest session cart into user cart seamlessly without duplicates."""
        if not session_key or not user:
            return

        try:
            guest_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
        except Cart.DoesNotExist:
            return

        user_cart, _ = Cart.objects.get_or_create(user=user)

        for guest_item in guest_cart.items.select_related('variant').all():
            variant = guest_item.variant
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                variant=variant,
                defaults={'quantity': 0}
            )
            # Combine quantities up to available stock
            combined_qty = user_item.quantity + guest_item.quantity
            user_item.quantity = min(combined_qty, variant.stock_quantity)
            if user_item.quantity > 0:
                user_item.save()

        # Delete guest cart after merge
        guest_cart.delete()
