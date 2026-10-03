import logging
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client

logger = logging.getLogger(__name__)
_notification_executor = ThreadPoolExecutor(max_workers=4)


def send_email_notification(subject, message, recipient):
    if not recipient:
        return False

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        return True

    except Exception as e:
        logger.warning(f"Email notification failed: {e}")
        return False


def send_sms_notification(message, phone_number):
    if not phone_number:
        return False

    if not getattr(settings, 'TWILIO_ACCOUNT_SID', None) or not getattr(settings, 'TWILIO_AUTH_TOKEN', None):
        return False

    try:
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )

        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number,
        )

        return True

    except Exception as e:
        logger.warning(f"SMS notification failed: {e}")
        return False


def _dispatch_order_confirmed_sync(order):
    user = order.user

    name = (
        user.first_name
        or user.username
        or "Customer"
    )

    email_sent = send_email_notification(
        subject=f"Order Confirmed: #{order.order_number} — StyleHub",
        message=(
            f"Hello {name},\n\n"
            f"Thank you for shopping at StyleHub!\n\n"
            f"Your order #{order.order_number} has been successfully confirmed.\n"
            f"Order Total: ₹{order.total_amount}\n\n"
            f"We are preparing your items for shipment.\n\n"
            f"Best regards,\n"
            f"StyleHub Team"
        ),
        recipient=user.email,
    )

    sms_sent = send_sms_notification(
        message=(
            f"StyleHub: Your order #{order.order_number} "
            f"has been confirmed. Total: ₹{order.total_amount}. "
            f"Thank you for shopping with us!"
        ),
        phone_number=order.shipping_phone,
    )

    return {
        "email": email_sent,
        "sms": sms_sent,
    }


def notify_order_confirmed(order, async_dispatch=True):
    """
    Send email and SMS confirmation for a successfully confirmed order.
    Dispatched in background thread by default so checkout response is instantaneous.
    Notification failures never break the order flow.
    """
    if async_dispatch:
        _notification_executor.submit(_dispatch_order_confirmed_sync, order)
        return {"status": "queued"}
    return _dispatch_order_confirmed_sync(order)