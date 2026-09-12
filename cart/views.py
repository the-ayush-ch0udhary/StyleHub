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

def api_cart_drawer(request):
    """Returns real-time cart data formatted for the slide-out mini cart drawer."""
    cart = CartService.get_or_create_cart(request)
    coupon_code = request.session.get('applied_coupon')
    coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first() if coupon_code else None
    totals = get_cart_totals(cart, coupon)

    items_data = []
    cart_product_ids = set()
    for item in cart.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images'):
        product = item.variant.product
        cart_product_ids.add(product.id)
        img = product.primary_image
        img_url = img.image.url if (img and img.image) else 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600&auto=format&fit=crop&q=80'
        items_data.append({
            'id': item.id,
            'product_name': product.name,
            'product_slug': product.slug,
            'product_brand': product.brand,
            'image_url': img_url,
            'size': item.variant.size,
            'color': item.variant.color,
            'unit_price': float(item.variant.current_price),
            'quantity': item.quantity,
            'total_price': float(item.total_price),
            'stock': item.variant.stock_quantity,
        })

    subtotal = float(totals['subtotal'])
    threshold = 999.0
    free_shipping_percent = min(100, int((subtotal / threshold) * 100)) if threshold > 0 else 100

    # Quick Add Accessory Upsell: find an active accessory not in cart
    from products.models import Product
    upsell_product = Product.objects.filter(
        is_active=True,
        category__slug__in=['accessories', 'footwear']
    ).exclude(id__in=cart_product_ids).prefetch_related('images', 'variants').first()

    upsell_data = None
    if upsell_product:
        v = upsell_product.variants.filter(is_active=True, stock_quantity__gt=0).first()
        if v:
            u_img = upsell_product.primary_image
            upsell_data = {
                'id': upsell_product.id,
                'name': upsell_product.name,
                'slug': upsell_product.slug,
                'price': float(upsell_product.discounted_price),
                'variant_id': v.id,
                'image_url': u_img.image.url if (u_img and u_img.image) else '',
            }

    return JsonResponse({
        'success': True,
        'items': items_data,
        'cart_count': cart.total_items,
        'subtotal': subtotal,
        'discount': float(totals['discount']),
        'shipping': float(totals['shipping']),
        'tax': float(totals['tax']),
        'total': float(totals['total']),
        'savings': float(totals['savings']),
        'free_shipping_eligible': totals['free_shipping_eligible'],
        'amount_needed_for_free_shipping': float(totals['amount_needed_for_free_shipping']),
        'free_shipping_percent': free_shipping_percent,
        'free_shipping_threshold': threshold,
        'upsell': upsell_data,
    })

@require_POST
def api_add_bundle(request):
    """Adds multiple products/variants from an outfit lookbook in 1 click."""
    import json
    from datetime import timedelta
    from django.utils import timezone
    from products.models import ProductVariant

    cart = CartService.get_or_create_cart(request)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    variant_ids = data.get('variant_ids', [])
    product_ids = data.get('product_ids', [])

    added_count = 0

    # If variant IDs provided
    for vid in variant_ids:
        try:
            s, _ = CartService.add_to_cart(cart, vid, 1)
            if s: added_count += 1
        except Exception:
            pass

    # If product IDs provided, pick first in-stock variant
    for pid in product_ids:
        v = ProductVariant.objects.filter(product_id=pid, is_active=True, stock_quantity__gt=0).first()
        if v:
            try:
                s, _ = CartService.add_to_cart(cart, v.id, 1)
                if s: added_count += 1
            except Exception:
                pass

    # Ensure BUNDLE10 coupon exists and apply
    bundle_coupon, _ = Coupon.objects.get_or_create(
        code='BUNDLE10',
        defaults={
            'discount_type': 'PERCENTAGE',
            'discount_value': 10.0,
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=365),
            'usage_limit': 10000,
            'is_active': True,
        }
    )
    request.session['applied_coupon'] = 'BUNDLE10'

    return JsonResponse({
        'success': added_count > 0,
        'added_count': added_count,
        'cart_count': cart.total_items,
        'message': f"Added complete outfit ({added_count} items) to your bag with 10% bundle savings!",
    })
