import logging
import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.conf import settings
from .models import Order, OrderItem
from accounts.models import Address
from accounts.forms import AddressForm
from cart.services import CartService
from cart.views import get_cart_totals
from coupons.models import Coupon
from products.models import ProductVariant

logger = logging.getLogger(__name__)

@login_required
def checkout_view(request):
    cart = CartService.get_or_create_cart(request)
    if cart.total_items == 0:
        messages.warning(request, "Your bag is empty! Add some fabulous styles first.")
        return redirect('products:shop')

    # Validate all items in cart have sufficient stock
    out_of_stock_items = []
    for item in cart.items.select_related('variant', 'variant__product'):
        if not item.variant.is_active or item.variant.stock_quantity < item.quantity:
            out_of_stock_items.append(f"{item.variant.product.name} ({item.variant.color}, {item.variant.size})")

    if out_of_stock_items:
        messages.error(request, f"Some items in your cart are no longer available in the requested quantity: {', '.join(out_of_stock_items)}. Please review your bag.")
        return redirect('cart:cart_detail')

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first() or addresses.first()

    coupon_code = request.session.get('applied_coupon')
    coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first() if coupon_code else None
    totals = get_cart_totals(cart, coupon)

    address_form = AddressForm()

    context = {
        'cart': cart,
        'items': cart.items.select_related('variant', 'variant__product'),
        'addresses': addresses,
        'default_address': default_address,
        'address_form': address_form,
        'coupon': coupon,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        **totals,
    }
    return render(request, 'checkout/checkout.html', context)

@login_required
def my_orders_view(request):
    status_filter = request.GET.get('status', '').strip()
    orders = Order.objects.filter(user=request.user).prefetch_related('items')

    if status_filter:
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'orders/my_orders.html', context)

@login_required
def order_detail_view(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__variant__product__images'), order_number=order_number, user=request.user)
    
    # Progress step calculation for tracking UI
    status_steps = [
        ('CONFIRMED', 'Order Confirmed', 'bi-check2-circle'),
        ('PROCESSING', 'Processing & Packed', 'bi-box-seam'),
        ('SHIPPED', 'Shipped with Courier', 'bi-truck'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery', 'bi-geo-alt'),
        ('DELIVERED', 'Delivered', 'bi-house-check'),
    ]

    current_idx = -1
    status_order = ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']
    if order.status in status_order:
        current_idx = status_order.index(order.status)
    elif order.status == 'CANCELLED':
        current_idx = -2

    context = {
        'order': order,
        'items': order.items.all(),
        'status_steps': status_steps,
        'current_step_idx': current_idx,
    }
    return render(request, 'orders/order_detail.html', context)

@login_required
@transaction.atomic
def order_cancel_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if request.method != 'POST':
        return redirect('orders:order_detail', order_number=order_number)

    if not order.is_cancellable:
        messages.error(request, f"Order #{order.order_number} cannot be cancelled as it has already reached status '{order.get_status_display()}'.")
        return redirect('orders:order_detail', order_number=order_number)

    # Restore inventory with row locks
    order_items = list(order.items.select_related('variant'))
    variant_ids = [item.variant_id for item in order_items if item.variant_id]
    locked_variants = {
        v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    }

    for item in order_items:
        variant = locked_variants.get(item.variant_id)
        if variant:
            variant.stock_quantity += item.quantity
            variant.save(update_fields=['stock_quantity', 'updated_at'])

    order.status = 'CANCELLED'
    refund_note = ""
    if order.payment_status == 'PAID':
        order.payment_status = 'REFUNDED'
        if order.payment_method == 'RAZORPAY' and order.razorpay_payment_id:
            try:
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                refund_payload = {
                    'amount': int(order.total_amount * 100),
                    'notes': {
                        'order_number': order.order_number,
                        'reason': 'Customer requested cancellation'
                    }
                }
                client.payment.refund(order.razorpay_payment_id, refund_payload)
                refund_note = "Your refund has been initiated to your original payment method via Razorpay."
            except Exception as e:
                logger.error(f"Razorpay refund initiation failed for order {order.order_number}: {e}")
                refund_note = "Cancellation recorded. Our support team will verify and process your refund within 2-3 business days."
        else:
            refund_note = "Your refund request has been queued."

    order.save()
    messages.success(request, f"Order #{order.order_number} has been cancelled successfully. {refund_note}")
    return redirect('orders:order_detail', order_number=order_number)

@login_required
def order_invoice_view(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number, user=request.user)
    return render(request, 'orders/invoice.html', {'order': order, 'items': order.items.all()})
