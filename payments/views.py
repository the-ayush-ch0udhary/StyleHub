import json
import razorpay

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db import transaction

from orders.models import Order, OrderItem
from accounts.models import Address
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

            # Re-check stock before completing payment
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

            # Create OrderItems
            for item in cart.items.select_related(
                'variant',
                'variant__product'
            ):

                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    sku=item.variant.sku,
                    size=item.variant.size,
                    color=item.variant.color,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.total_price,
                )

                # Reduce stock
                item.variant.stock_quantity = max(
                    0,
                    item.variant.stock_quantity - item.quantity
                )

                item.variant.save()

            # Record coupon usage
            if order.coupon_code:

                coupon = Coupon.objects.filter(
                    code__iexact=order.coupon_code
                ).first()

                if coupon:
                    coupon.used_count += 1
                    coupon.save()

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

        for item in cart.items.select_related(
            'variant',
            'variant__product'
        ):

            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                product_name=item.variant.product.name,
                sku=item.variant.sku,
                size=item.variant.size,
                color=item.variant.color,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.total_price,
            )

            item.variant.stock_quantity = max(
                0,
                item.variant.stock_quantity - item.quantity
            )

            item.variant.save()

        # Coupon usage
        if order.coupon_code:

            coupon = Coupon.objects.filter(
                code__iexact=order.coupon_code
            ).first()

            if coupon:
                coupon.used_count += 1
                coupon.save()

                CouponUsage.objects.create(
                    coupon=coupon,
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