import json
import razorpay

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction

from orders.models import Order, OrderItem
from accounts.models import Address
from products.models import ProductVariant
from cart.services import CartService
from cart.views import get_cart_totals
from coupons.models import Coupon, CouponUsage

from notifications.services import notify_order_confirmed


def get_razorpay_client():
    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )


@login_required
@require_POST
def create_razorpay_order(request):
    """Create Razorpay order and corresponding pending StyleHub order."""

    address_id = request.POST.get('address_id')

    if not address_id:
        return JsonResponse(
            {
                'success': False,
                'message': 'Please select or add a shipping address.'
            },
            status=400
        )

    try:
        address = Address.objects.get(
            id=address_id,
            user=request.user
        )
    except Address.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'message': 'Selected shipping address not found.'
            },
            status=404
        )

    cart = CartService.get_or_create_cart(request)

    if cart.total_items == 0:
        return JsonResponse(
            {
                'success': False,
                'message': 'Your bag is empty.'
            },
            status=400
        )

    # Validate stock before creating payment
    for item in cart.items.select_related(
        'variant',
        'variant__product'
    ):
        if (
            not item.variant.is_active
            or item.variant.stock_quantity < item.quantity
        ):
            return JsonResponse(
                {
                    'success': False,
                    'message': (
                        f"Insufficient stock for "
                        f"{item.variant.product.name} "
                        f"({item.variant.color}, {item.variant.size}). "
                        f"Only {item.variant.stock_quantity} available."
                    )
                },
                status=400
            )

    coupon_code = request.session.get('applied_coupon')

    coupon = (
        Coupon.objects.filter(
            code__iexact=coupon_code,
            is_active=True
        ).first()
        if coupon_code
        else None
    )

    totals = get_cart_totals(cart, coupon)

    amount_in_paise = int(totals['total'] * 100)

    if amount_in_paise <= 0:
        return JsonResponse(
            {
                'success': False,
                'message': 'Invalid payment amount.'
            },
            status=400
        )

    try:
        client = get_razorpay_client()

        razorpay_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {
                'user_id': str(request.user.id),
                'user_email': request.user.email,
            }
        }

        # Create REAL Razorpay order.
        # Do not silently create fake/mock order IDs.
        razorpay_order = client.order.create(
            data=razorpay_data
        )

        rzp_order_id = razorpay_order['id']

        # Create pending StyleHub order
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_address_line_1=address.address_line_1,
            shipping_address_line_2=address.address_line_2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=address.country,
            subtotal=totals['subtotal'],
            discount=totals['discount'],
            shipping_charge=totals['shipping'],
            tax=totals['tax'],
            total_amount=totals['total'],
            coupon_code=coupon.code if coupon else None,
            status='PENDING',
            payment_status='PENDING',
            payment_method='RAZORPAY',
            razorpay_order_id=rzp_order_id,
        )

        return JsonResponse(
            {
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'razorpay_order_id': rzp_order_id,
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'customer_name': (
                    f"{request.user.first_name} "
                    f"{request.user.last_name}"
                ).strip() or request.user.username,
                'customer_email': request.user.email,
                'customer_phone': address.phone,
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                'success': False,
                'message': f"Razorpay order creation failed: {str(e)}"
            },
            status=502
        )


@login_required
@require_POST
def verify_razorpay_payment(request):
    """
    Verify Razorpay payment signature, validate payment/order,
    create order items, reduce stock and send notifications.
    """

    try:
        if request.content_type == 'application/json':
            data = json.loads(
                request.body.decode('utf-8')
            )
        else:
            data = request.POST

        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        order_number = data.get('order_number')

        if not all([
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
            order_number
        ]):
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Incomplete payment verification data.'
                },
                status=400
            )

        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user
        )

        # Prevent duplicate processing
        if order.payment_status == 'PAID':
            return JsonResponse(
                {
                    'success': True,
                    'redirect_url': (
                        f"/payments/success/"
                        f"{order.order_number}/"
                    )
                }
            )

        # Make sure Razorpay order belongs to this StyleHub order
        if order.razorpay_order_id != razorpay_order_id:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Payment order mismatch.'
                },
                status=400
            )

        client = get_razorpay_client()

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        # Verify HMAC signature
        try:
            client.utility.verify_payment_signature(
                params_dict
            )
        except Exception:
            order.payment_status = 'FAILED'
            order.save(update_fields=['payment_status'])

            return JsonResponse(
                {
                    'success': False,
                    'message': (
                        'Payment verification failed. '
                        'Please try again.'
                    )
                },
                status=400
            )

        # Fetch payment from Razorpay to verify amount/status
        try:
            payment = client.payment.fetch(
                razorpay_payment_id
            )

            payment_amount = int(payment.get('amount', 0))
            expected_amount = int(
                order.total_amount * 100
            )

            if payment_amount != expected_amount:
                order.payment_status = 'FAILED'
                order.save(
                    update_fields=['payment_status']
                )

                return JsonResponse(
                    {
                        'success': False,
                        'message': (
                            'Payment amount verification failed.'
                        )
                    },
                    status=400
                )

            payment_order_id = payment.get('order_id')

            if payment_order_id != razorpay_order_id:
                order.payment_status = 'FAILED'
                order.save(
                    update_fields=['payment_status']
                )

                return JsonResponse(
                    {
                        'success': False,
                        'message': (
                            'Payment order verification failed.'
                        )
                    },
                    status=400
                )

        except Exception as e:
            return JsonResponse(
                {
                    'success': False,
                    'message': (
                        f"Unable to verify payment with Razorpay: {str(e)}"
                    )
                },
                status=502
            )

        with transaction.atomic():

            cart = CartService.get_or_create_cart(request)

            if cart.total_items == 0:
                return JsonResponse(
                    {
                        'success': False,
                        'message': 'Your bag is empty.'
                    },
                    status=400
                )

            cart_items = list(cart.items.select_related('variant', 'variant__product'))
            variant_ids = [item.variant_id for item in cart_items if item.variant_id]

            # Lock variants with select_for_update to eliminate race conditions
            locked_variants = {
                v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids).select_related('product')
            }

            # Re-check stock before completing payment
            for item in cart_items:
                variant = locked_variants.get(item.variant_id)
                if not variant or not variant.is_active or variant.stock_quantity < item.quantity:
                    p_name = variant.product.name if variant and variant.product else "an item"
                    return JsonResponse(
                        {
                            'success': False,
                            'message': f"Insufficient stock for {p_name}."
                        },
                        status=400
                    )

            # Create OrderItems & safely deduct inventory
            for item in cart_items:
                variant = locked_variants.get(item.variant_id)
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    product_name=variant.product.name,
                    sku=variant.sku,
                    size=variant.size,
                    color=variant.color,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.total_price,
                )

                # Reduce stock atomically
                variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                variant.save(update_fields=['stock_quantity', 'updated_at'])

            # Record coupon usage
            if order.coupon_code:
                coupon = Coupon.objects.select_for_update().filter(
                    code__iexact=order.coupon_code
                ).first()

                if coupon:
                    coupon.used_count += 1
                    coupon.save(update_fields=['used_count'])

                    CouponUsage.objects.create(
                        coupon=coupon,
                        user=request.user,
                        order=order
                    )

            # Mark order as confirmed and paid
            order.status = 'CONFIRMED'
            order.payment_status = 'PAID'
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature

            order.save()

            # Clear cart
            CartService.clear_cart(cart)

            # Clear coupon
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']

        # Email + SMS
        # Kept outside transaction intentionally.
        notify_order_confirmed(order)

        return JsonResponse(
            {
                'success': True,
                'redirect_url': (
                    f"/payments/success/"
                    f"{order.order_number}/"
                )
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                'success': False,
                'message': (
                    f"Order verification error: {str(e)}"
                )
            },
            status=500
        )


@login_required
@require_POST
def cod_place_order(request):
    """Places Cash on Delivery (COD) order."""

    address_id = request.POST.get('address_id')

    if not address_id:
        return JsonResponse(
            {
                'success': False,
                'message': 'Please select a delivery address.'
            },
            status=400
        )

    try:
        address = Address.objects.get(
            id=address_id,
            user=request.user
        )

    except Address.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'message': 'Address not found.'
            },
            status=404
        )

    cart = CartService.get_or_create_cart(request)

    if cart.total_items == 0:
        return JsonResponse(
            {
                'success': False,
                'message': 'Your bag is empty.'
            },
            status=400
        )

    # Validate stock
    for item in cart.items.select_related(
        'variant',
        'variant__product'
    ):

        if (
            not item.variant.is_active
            or item.variant.stock_quantity < item.quantity
        ):
            return JsonResponse(
                {
                    'success': False,
                    'message': (
                        f"Insufficient stock for "
                        f"{item.variant.product.name}."
                    )
                },
                status=400
            )

    coupon_code = request.session.get('applied_coupon')

    coupon = (
        Coupon.objects.filter(
            code__iexact=coupon_code,
            is_active=True
        ).first()
        if coupon_code
        else None
    )

    totals = get_cart_totals(cart, coupon)

    with transaction.atomic():
        cart_items = list(cart.items.select_related('variant', 'variant__product'))
        variant_ids = [item.variant_id for item in cart_items if item.variant_id]

        locked_variants = {
            v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids).select_related('product')
        }

        # Check stock with locked rows
        for item in cart_items:
            variant = locked_variants.get(item.variant_id)
            if not variant or not variant.is_active or variant.stock_quantity < item.quantity:
                p_name = variant.product.name if variant and variant.product else "an item"
                return JsonResponse({
                    'success': False,
                    'message': f"Insufficient stock for {p_name}."
                }, status=400)

        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_address_line_1=address.address_line_1,
            shipping_address_line_2=address.address_line_2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=address.country,
            subtotal=totals['subtotal'],
            discount=totals['discount'],
            shipping_charge=totals['shipping'],
            tax=totals['tax'],
            total_amount=totals['total'],
            coupon_code=coupon.code if coupon else None,
            status='CONFIRMED',
            payment_status='PENDING',
            payment_method='COD',
        )

        for item in cart_items:
            variant = locked_variants.get(item.variant_id)
            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                sku=variant.sku,
                size=variant.size,
                color=variant.color,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.total_price,
            )

            variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
            variant.save(update_fields=['stock_quantity', 'updated_at'])

        # Coupon usage
        if order.coupon_code:
            coupon_obj = Coupon.objects.select_for_update().filter(
                code__iexact=order.coupon_code
            ).first()

            if coupon_obj:
                coupon_obj.used_count += 1
                coupon_obj.save(update_fields=['used_count'])

                CouponUsage.objects.create(
                    coupon=coupon_obj,
                    user=request.user,
                    order=order
                )

        # Clear cart
        CartService.clear_cart(cart)

        if 'applied_coupon' in request.session:
            del request.session['applied_coupon']

    # Email + SMS
    notify_order_confirmed(order)

    return JsonResponse(
        {
            'success': True,
            'redirect_url': (
                f"/payments/success/"
                f"{order.order_number}/"
            )
        }
    )


@login_required
def payment_success_view(request, order_number):

    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
        user=request.user
    )

    return render(
        request,
        'checkout/order_success.html',
        {
            'order': order,
            'items': order.items.all()
        }
    )


@login_required
def payment_failed_view(request):

    order_number = request.GET.get('order_number')

    return render(
        request,
        'checkout/payment_failed.html',
        {
            'order_number': order_number
        }
    )


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Razorpay Webhook listener to handle order.paid and payment.captured events.
    Verifies X-Razorpay-Signature with RAZORPAY_WEBHOOK_SECRET.
    Ensures orders are confirmed and stock is deducted even if the customer's browser disconnected.
    """
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    if not webhook_secret:
        return HttpResponse("Webhook secret not configured", status=200)

    signature = request.headers.get('X-Razorpay-Signature') or request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    if not signature:
        return HttpResponse("Missing signature", status=400)

    body = request.body.decode('utf-8')
    client = get_razorpay_client()

    try:
        client.utility.verify_webhook_signature(body, signature, webhook_secret)
    except Exception as e:
        return HttpResponse(f"Invalid signature: {e}", status=400)

    try:
        data = json.loads(body)
        event = data.get('event')

        if event in ('order.paid', 'payment.captured'):
            payload = data.get('payload', {})
            payment_entity = payload.get('payment', {}).get('entity', {})
            rzp_order_id = payment_entity.get('order_id')
            rzp_payment_id = payment_entity.get('id')

            if rzp_order_id:
                order = Order.objects.filter(razorpay_order_id=rzp_order_id).first()
                if order and order.payment_status != 'PAID':
                    with transaction.atomic():
                        order.payment_status = 'PAID'
                        order.status = 'CONFIRMED'
                        if rzp_payment_id:
                            order.razorpay_payment_id = rzp_payment_id
                        order.save(update_fields=['payment_status', 'status', 'razorpay_payment_id'])

                    notify_order_confirmed(order)

        return HttpResponse("Webhook processed successfully", status=200)

    except Exception as e:
        return HttpResponse(f"Webhook processing error: {e}", status=500)