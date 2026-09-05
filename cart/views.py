from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from decimal import Decimal
from .services import CartService
from .models import CartItem
from coupons.models import Coupon

def get_cart_totals(cart, coupon=None):
    """Calculates subtotal, discount, shipping, tax, and grand total."""
    subtotal = cart.subtotal
    discount = Decimal('0.00')

    if coupon and coupon.is_valid_for_cart(subtotal):
        discount = coupon.calculate_discount(subtotal)

    taxable_amount = max(Decimal('0.00'), subtotal - discount)
    # Free shipping on orders above ₹999
    shipping = Decimal('0.00') if taxable_amount >= Decimal('999.00') or taxable_amount == 0 else Decimal('99.00')
    tax = round(taxable_amount * Decimal('0.05'), 2)  # 5% apparel GST
    total = taxable_amount + shipping + tax

    return {
        'subtotal': subtotal,
        'original_total': cart.total_original_price,
        'savings': cart.total_savings,
        'discount': discount,
        'shipping': shipping,
        'tax': tax,
        'total': total,
        'free_shipping_eligible': taxable_amount >= Decimal('999.00'),
        'free_shipping_threshold': Decimal('999.00'),
        'amount_needed_for_free_shipping': max(Decimal('0.00'), Decimal('999.00') - taxable_amount),
    }

def cart_detail_view(request):
    cart = CartService.get_or_create_cart(request)
    coupon_code = request.session.get('applied_coupon')
    coupon = None
    if coupon_code:
        coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first()

    totals = get_cart_totals(cart, coupon)

    context = {
        'cart': cart,
        'items': cart.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images'),
        'coupon': coupon,
        **totals,
    }
    return render(request, 'cart/cart.html', context)

@require_POST
def api_add_to_cart(request):
    variant_id = request.POST.get('variant_id')
    quantity = request.POST.get('quantity', 1)

    if not variant_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Please select a size and color.'}, status=400)
        messages.error(request, 'Please select a size and color.')
        return redirect(request.META.get('HTTP_REFERER', 'products:shop'))

    cart = CartService.get_or_create_cart(request)
    success, message = CartService.add_to_cart(cart, variant_id, quantity)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message,
            'cart_count': cart.total_items,
            'cart_subtotal': float(cart.subtotal),
        })

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

@require_POST
def api_update_cart(request):
    item_id = request.POST.get('item_id')
    quantity = request.POST.get('quantity')

    if not item_id or quantity is None:
        return JsonResponse({'success': False, 'message': 'Invalid parameters'}, status=400)

    cart = CartService.get_or_create_cart(request)
    success, message = CartService.update_cart_item(cart, item_id, quantity)

    coupon_code = request.session.get('applied_coupon')
    coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first() if coupon_code else None
    totals = get_cart_totals(cart, coupon)

    item = CartItem.objects.filter(id=item_id, cart=cart).first()
    item_total = float(item.total_price) if item else 0.0

    return JsonResponse({
        'success': success,
        'message': message,
        'item_id': item_id,
        'item_total': item_total,
        'cart_count': cart.total_items,
        'subtotal': float(totals['subtotal']),
        'discount': float(totals['discount']),
        'shipping': float(totals['shipping']),
        'tax': float(totals['tax']),
        'total': float(totals['total']),
        'savings': float(totals['savings']),
        'amount_needed_for_free_shipping': float(totals['amount_needed_for_free_shipping']),
    })

@require_POST
def api_remove_cart(request):
    item_id = request.POST.get('item_id')
    cart = CartService.get_or_create_cart(request)
    success, message = CartService.remove_from_cart(cart, item_id)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        coupon_code = request.session.get('applied_coupon')
        coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first() if coupon_code else None
        totals = get_cart_totals(cart, coupon)

        return JsonResponse({
            'success': success,
            'message': message,
            'cart_count': cart.total_items,
            'subtotal': float(totals['subtotal']),
            'discount': float(totals['discount']),
            'shipping': float(totals['shipping']),
            'tax': float(totals['tax']),
            'total': float(totals['total']),
            'savings': float(totals['savings']),
        })

    messages.info(request, message)
    return redirect('cart:cart_detail')

@require_POST
def api_clear_cart(request):
    cart = CartService.get_or_create_cart(request)
    CartService.clear_cart(cart)
    messages.info(request, "Your bag has been emptied.")
    return redirect('cart:cart_detail')
