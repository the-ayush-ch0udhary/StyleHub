from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client


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
        print(f"Email notification failed: {e}")
        return False


def send_sms_notification(message, phone_number):
    if not phone_number:
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
        print(f"SMS notification failed: {e}")
        return False


def notify_order_confirmed(order):
    """
    Send email and SMS confirmation for a successfully confirmed order.

    Notification failures should never break the order flow.
    """

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