from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count, Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.contrib import messages
from .models import Category, Product, ProductImage, ProductVariant

def home_view(request):
    featured_categories = Category.objects.filter(is_active=True)[:8]
    featured_products = Product.objects.filter(is_active=True, is_featured=True).prefetch_related('images', 'variants')[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at').prefetch_related('images', 'variants')[:8]
    bestsellers = Product.objects.filter(is_active=True, is_bestseller=True).prefetch_related('images', 'variants')[:8]

    context = {
        'featured_categories': featured_categories,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'bestsellers': bestsellers,
    }
    return render(request, 'products/home.html', context)

def shop_view(request):
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants')

    # Extract filter parameters
    category_slug = request.GET.get('category', '').strip()
    brand_param = request.GET.get('brand', '').strip()
    size_param = request.GET.get('size', '').strip()
    color_param = request.GET.get('color', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    rating_param = request.GET.get('rating', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()
    search_query = request.GET.get('q', '').strip()

    # Apply Search Query
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Apply Category Filter
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=selected_category)

    # Apply Brand Filter
    if brand_param:
        products = products.filter(brand__iexact=brand_param)

    # Apply Variant Filters (Size, Color)
    if size_param:
        products = products.filter(variants__size__iexact=size_param, variants__is_active=True)

    if color_param:
        products = products.filter(variants__color__iexact=color_param, variants__is_active=True)

    # Apply Price Range Filter
    if min_price and min_price.isdigit():
        products = products.filter(base_price__gte=Decimal(min_price) if False else float(min_price))
    if max_price and max_price.isdigit():
        products = products.filter(base_price__lte=Decimal(max_price) if False else float(max_price))

    # Apply Rating Filter
    if rating_param and rating_param.isdigit():
        min_rating = float(rating_param)
        products = products.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=min_rating)

    # Distinct query after joins
    products = products.distinct()

    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('base_price')
    elif sort_by == 'price_high':
        products = products.order_by('-base_price')
    elif sort_by == 'popularity':
        products = products.order_by('-is_bestseller', '-created_at')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating', '-created_at')
    else:  # newest
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    # Filter Sidebar Metadata
    all_categories = Category.objects.filter(is_active=True).annotate(p_count=Count('products', filter=Q(products__is_active=True)))
    all_brands = Product.objects.filter(is_active=True).values_list('brand', flat=True).distinct().order_by('brand')
    all_sizes = ProductVariant.objects.filter(is_active=True).values_list('size', flat=True).distinct()
    all_colors = ProductVariant.objects.filter(is_active=True).values('color', 'color_code').distinct()

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': products.count(),
        'all_categories': all_categories,
        'all_brands': all_brands,
        'all_sizes': all_sizes,
        'all_colors': all_colors,
        'selected_category': selected_category,
        'current_category': category_slug,
        'current_brand': brand_param,
        'current_size': size_param,
        'current_color': color_param,
        'current_min_price': min_price,
        'current_max_price': max_price,
        'current_rating': rating_param,
        'current_sort': sort_by,
        'search_query': search_query,
    }
    return render(request, 'products/shop.html', context)

def product_detail_view(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images', 'variants', 'reviews__user'),
        slug=slug,
        is_active=True
    )

    variants = product.variants.filter(is_active=True).order_by('size', 'color')
    related_products = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]

    # Check if user has purchased this product for verified review badge/form
    user_has_purchased = False
    if request.user.is_authenticated:
        from orders.models import OrderItem
        user_has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            variant__product=product,
            order__status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']
        ).exists()

    user_existing_review = None
    if request.user.is_authenticated:
        user_existing_review = product.reviews.filter(user=request.user).first()

    context = {
        'product': product,
        'variants': variants,
        'images': product.images.all(),
        'related_products': related_products,
        'rating_distribution': product.get_rating_distribution(),
        'user_has_purchased': user_has_purchased,
        'user_existing_review': user_existing_review,
        'available_sizes': product.get_available_sizes(),
        'available_colors': product.get_available_colors(),
    }
    return render(request, 'products/product_detail.html', context)

def api_variant_stock(request):
    """AJAX endpoint returning specific variant details for selected color and size."""
    product_id = request.GET.get('product_id')
    color = request.GET.get('color', '').strip()
    size = request.GET.get('size', '').strip()

    if not product_id:
        return JsonResponse({'success': False, 'error': 'Product ID is required'}, status=400)

    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)

    variants = product.variants.filter(is_active=True)
    if color and size:
        variant = variants.filter(color__iexact=color, size__iexact=size).first()
        if variant:
            return JsonResponse({
                'success': True,
                'variant_id': variant.id,
                'sku': variant.sku,
                'price': float(variant.current_price),
                'stock_quantity': variant.stock_quantity,
                'in_stock': variant.is_in_stock,
                'color': variant.color,
                'size': variant.size,
            })
        else:
            return JsonResponse({
                'success': False,
                'in_stock': False,
                'message': 'This variant combination is currently unavailable.'
            })
    elif color:
        available_sizes = list(variants.filter(color__iexact=color, stock_quantity__gt=0).values_list('size', flat=True))
        return JsonResponse({
            'success': True,
            'available_sizes': available_sizes
        })
    elif size:
        available_colors = list(variants.filter(size__iexact=size, stock_quantity__gt=0).values_list('color', flat=True))
        return JsonResponse({
            'success': True,
            'available_colors': available_colors
        })

    return JsonResponse({'success': False, 'error': 'Invalid parameters'}, status=400)

def search_view(request):
    query = request.GET.get('q', '').strip()
    return shop_view(request)

def newsletter_subscribe_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email and '@' in email:
            messages.success(request, "Thank you for subscribing to the StyleHub newsletter! Check your inbox for exclusive perks.")
        else:
            messages.error(request, "Please enter a valid email address.")
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))
