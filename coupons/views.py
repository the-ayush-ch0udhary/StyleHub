from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from cart.services import CartService
from cart.views import get_cart_totals
from .models import Coupon

@require_POST
def api_apply_coupon(request):
    code = request.POST.get('coupon_code', '').strip().upper()
    if not code:
        return JsonResponse({'success': False, 'message': 'Please enter a coupon code.'}, status=400)

    coupon = Coupon.objects.filter(code__iexact=code).first()
    if not coupon:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code.'}, status=404)

    if not coupon.is_valid_now():
        return JsonResponse({'success': False, 'message': 'This coupon has expired or reached its usage limit.'}, status=400)

    cart = CartService.get_or_create_cart(request)
    subtotal = cart.subtotal

    if subtotal < coupon.minimum_order_amount:
        return JsonResponse({
            'success': False,
            'message': f'Minimum order amount of ₹{coupon.minimum_order_amount} required to apply this coupon.'
        }, status=400)

    # Save coupon in session
    request.session['applied_coupon'] = coupon.code
    totals = get_cart_totals(cart, coupon)

    discount_str = f"{int(coupon.discount_value)}%" if coupon.discount_type == 'PERCENTAGE' else f"₹{coupon.discount_value}"

    return JsonResponse({
        'success': True,
        'message': f'Coupon "{coupon.code}" applied! You saved ₹{totals["discount"]} ({discount_str} off).',
        'coupon_code': coupon.code,
        'discount': float(totals['discount']),
        'subtotal': float(totals['subtotal']),
        'shipping': float(totals['shipping']),
        'tax': float(totals['tax']),
        'total': float(totals['total']),
    })

@require_POST
def api_remove_coupon(request):
    if 'applied_coupon' in request.session:
        del request.session['applied_coupon']

    cart = CartService.get_or_create_cart(request)
    totals = get_cart_totals(cart, None)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Coupon removed.',
            'discount': 0.0,
            'subtotal': float(totals['subtotal']),
            'shipping': float(totals['shipping']),
            'tax': float(totals['tax']),
            'total': float(totals['total']),
        })

    messages.info(request, "Coupon removed.")
    return redirect('cart:cart_detail')
