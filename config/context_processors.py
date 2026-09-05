from django.conf import settings

def theme_context(request):
    """Provides global site-wide context variables."""
    return {
        'SITE_NAME': 'StyleHub',
        'SITE_TAGLINE': 'Modern Luxury Fashion & Everyday Essentials',
        'CURRENCY_SYMBOL': '₹',
        'RAZORPAY_KEY_ID': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
