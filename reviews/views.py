from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Review
from products.models import Product
from orders.models import OrderItem

@login_required
@require_POST
def add_review_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    # Check verified purchase
    is_verified = OrderItem.objects.filter(
        order__user=request.user,
        variant__product=product,
        order__status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']
    ).exists()

    if not is_verified:
        messages.error(request, "Only verified purchasers who ordered this product can submit a review.")
        return redirect('products:product_detail', slug=product.slug)

    try:
        rating = int(request.POST.get('rating', 5))
        if rating < 1 or rating > 5:
            rating = 5
    except ValueError:
        rating = 5

    title = request.POST.get('title', '').strip()
    comment = request.POST.get('comment', '').strip()

    if not comment:
        messages.error(request, "Please write your review thoughts before submitting.")
        return redirect('products:product_detail', slug=product.slug)

    review, created = Review.objects.update_or_create(
        user=request.user,
        product=product,
        defaults={
            'rating': rating,
            'title': title,
            'comment': comment,
            'is_verified_purchase': True,
        }
    )

    if created:
        messages.success(request, "Thank you! Your review and rating have been posted.")
    else:
        messages.success(request, "Your review has been updated.")

    return redirect('products:product_detail', slug=product.slug)
