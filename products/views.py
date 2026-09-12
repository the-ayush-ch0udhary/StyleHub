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

    # Up to 10 dynamic clothes/products for the interactive hero carousel
    hero_qs = Product.objects.filter(is_active=True, is_featured=True).prefetch_related('images', 'variants', 'category')[:10]
    hero_products = list(hero_qs)
    if len(hero_products) < 10:
        existing_ids = {p.id for p in hero_products}
        additional = (
            Product.objects.filter(is_active=True)
            .exclude(id__in=existing_ids)
            .prefetch_related('images', 'variants', 'category')[:10 - len(hero_products)]
        )
        hero_products.extend(list(additional))

    # Curated "Shop The Look" Outfit Lookbook Bundle
    bundle_pids = [18, 5, 4, 11] # Denim Jacket, Boxy Tee, Selvedge Denim, Urban Sneakers
    products_by_id = {p.id: p for p in Product.objects.filter(id__in=bundle_pids, is_active=True).prefetch_related('images', 'variants')}
    
    pin_configs = [
        {'id': 18, 'label': 'Layer 1: Denim Jacket', 'top': 30, 'left': 44},
        {'id': 5, 'label': 'Layer 2: Boxy Crewneck', 'top': 46, 'left': 56},
        {'id': 4, 'label': 'Bottom: Selvedge Denim', 'top': 68, 'left': 45},
        {'id': 11, 'label': 'Footwear: Urban Sneakers', 'top': 88, 'left': 53},
    ]

    lookbook_items = []
    bundle_subtotal = 0
    for cfg in pin_configs:
        prod = products_by_id.get(cfg['id'])
        if prod:
            lookbook_items.append({
                'product': prod,
                'label': cfg['label'],
                'top': cfg['top'],
                'left': cfg['left'],
            })
            bundle_subtotal += float(prod.discounted_price)

    bundle_discount = round(bundle_subtotal * 0.10, 2)
    bundle_total = round(bundle_subtotal - bundle_discount, 2)
    bundle_product_ids = [item['product'].id for item in lookbook_items]

    context = {
        'featured_categories': featured_categories,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'bestsellers': bestsellers,
        'hero_products': hero_products,
        'lookbook_items': lookbook_items,
        'bundle_subtotal': bundle_subtotal,
        'bundle_discount': bundle_discount,
        'bundle_total': bundle_total,
        'bundle_product_ids': bundle_product_ids,
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

    # Filter Sidebar Metadata (Deduplicated & Logically Ordered)
    all_categories = Category.objects.filter(is_active=True).annotate(p_count=Count('products', filter=Q(products__is_active=True)))
    all_brands = Product.objects.filter(is_active=True).order_by('brand').values_list('brand', flat=True).distinct()
    
    # Custom logical sorting for apparel and footwear sizes without duplicates
    SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '28', '30', '32', '34', '36', 'UK 6', 'UK 7', 'UK 8', 'UK 9', 'UK 10', 'UK 11', 'Free Size']
    raw_sizes = list(ProductVariant.objects.filter(is_active=True).order_by().values_list('size', flat=True).distinct())
    all_sizes = sorted(raw_sizes, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else 999)

    # Clean deduplicated colors list
    seen_colors = set()
    all_colors = []
    for c in ProductVariant.objects.filter(is_active=True).order_by('color').values('color', 'color_code'):
        c_name = c['color'].strip()
        if c_name not in seen_colors:
            seen_colors.add(c_name)
            all_colors.append({
                'color': c_name,
                'color_code': c['color_code'] or '#222222',
            })

    active_filter_count = sum(bool(x) for x in [category_slug, brand_param, size_param, color_param, min_price, max_price, rating_param])

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
        'active_filter_count': active_filter_count,
    }
    return render(request, 'products/shop.html', context)

def classify_wardrobe_item(product):
    name_lower = product.name.lower()
    cat_slug = product.category.slug.lower()
    is_women = (
        cat_slug == 'women'
        or any(k in name_lower for k in ['dress', 'skirt', 'fitted top', 'women', 'wrap'])
    )

    if any(k in name_lower for k in ['dress', 'slip']):
        archetype = 'dress'
        label = 'Dress'
    elif cat_slug in ['jackets', 'hoodies'] or any(k in name_lower for k in ['jacket', 'bomber', 'overcoat', 'hoodie', 'coat']):
        archetype = 'outerwear'
        label = 'Outerwear'
    elif cat_slug == 'denim' or any(k in name_lower for k in ['denim', 'jeans', 'trousers', 'pants']):
        archetype = 'bottoms'
        label = 'Bottoms'
    elif cat_slug == 'footwear' or any(k in name_lower for k in ['sneakers', 'shoes', 'low-top', 'runners']):
        archetype = 'footwear'
        label = 'Footwear'
    elif cat_slug == 'accessories' or any(k in name_lower for k in ['belt', 'bag', 'cap', 'wallet']):
        archetype = 'accessories'
        label = 'Accessory'
    elif cat_slug in ['shirts'] or any(k in name_lower for k in ['shirt', 't-shirt', 'tee', 'top', 'crewneck']):
        archetype = 'tops'
        label = 'Top'
    else:
        archetype = 'tops'
        label = 'Top'

    return archetype, label, is_women

def build_outfit_pairings(target_product):
    target_arch, _, target_is_women = classify_wardrobe_item(target_product)

    # Wardrobe recipe for each clothing type
    if target_arch == 'bottoms':
        recipe = [('tops', 'Top'), ('outerwear', 'Outerwear'), ('footwear', 'Footwear'), ('accessories', 'Accessory')]
    elif target_arch == 'outerwear':
        recipe = [('tops', 'Inner Top'), ('bottoms', 'Bottoms'), ('footwear', 'Footwear'), ('accessories', 'Accessory')]
    elif target_arch == 'tops':
        recipe = [('bottoms', 'Bottoms'), ('outerwear', 'Layering Piece'), ('footwear', 'Footwear'), ('accessories', 'Accessory')]
    elif target_arch == 'dress':
        recipe = [('outerwear', 'Outer Layer'), ('footwear', 'Footwear'), ('accessories', 'Accessory'), ('tops', 'Inner Layer')]
    elif target_arch == 'footwear':
        recipe = [('bottoms', 'Bottoms'), ('tops', 'Top'), ('outerwear', 'Outerwear'), ('accessories', 'Accessory')]
    elif target_arch == 'accessories':
        recipe = [('bottoms', 'Bottoms'), ('tops', 'Top'), ('outerwear', 'Outerwear'), ('footwear', 'Footwear')]
    else:
        recipe = [('tops', 'Top'), ('bottoms', 'Bottoms'), ('outerwear', 'Outerwear'), ('footwear', 'Footwear')]

    all_products = list(
        Product.objects.filter(is_active=True)
        .exclude(pk=target_product.pk)
        .prefetch_related('images', 'variants', 'category')
    )

    outfit = []
    used_ids = {target_product.pk}

    for needed_arch, role_name in recipe:
        candidates_matching_gender = []
        candidates_fallback = []
        for p in all_products:
            if p.pk in used_ids:
                continue
            arch, _, is_w = classify_wardrobe_item(p)
            if arch == needed_arch:
                if target_is_women == is_w:
                    candidates_matching_gender.append(p)
                elif not is_w:
                    candidates_fallback.append(p)
                else:
                    candidates_fallback.append(p)

        chosen = None
        if candidates_matching_gender:
            chosen = candidates_matching_gender[0]
        elif candidates_fallback:
            chosen = candidates_fallback[0]

        if chosen:
            chosen.outfit_role = role_name
            outfit.append(chosen)
            used_ids.add(chosen.pk)

    return outfit

def product_detail_view(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images', 'variants', 'reviews__user'),
        slug=slug,
        is_active=True
    )

    variants = product.variants.filter(is_active=True).order_by('size', 'color')

    # 1. More Like This: Same category (or same brand), excluding current product
    more_like_this_qs = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=product.pk).prefetch_related('images', 'variants')[:4]
    more_like_this = list(more_like_this_qs)
    if len(more_like_this) < 4:
        existing_ids = {product.pk} | {p.pk for p in more_like_this}
        backfill = Product.objects.filter(
            is_active=True
        ).exclude(pk__in=existing_ids).prefetch_related('images', 'variants')[:4 - len(more_like_this)]
        more_like_this.extend(list(backfill))

    # 2. Complete The Style (Outfit Coordination):
    # Construct an actual wearable outfit (Top + Bottom + Footwear + Accessory)
    complete_style = build_outfit_pairings(product)

    # 3. Recommended For You: Top trending & bestsellers across the store
    seen_ids = {product.pk} | {p.pk for p in more_like_this} | {p.pk for p in complete_style}
    recommended_qs = Product.objects.filter(
        is_active=True
    ).filter(
        Q(is_bestseller=True) | Q(is_featured=True)
    ).exclude(pk__in=seen_ids).prefetch_related('images', 'variants')[:4]
    recommended_for_you = list(recommended_qs)
    if len(recommended_for_you) < 4:
        seen_ids |= {p.pk for p in recommended_for_you}
        recommended_for_you.extend(list(
            Product.objects.filter(is_active=True).exclude(pk__in=seen_ids).prefetch_related('images', 'variants')[:4 - len(recommended_for_you)]
        ))

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

    # User wishlist IDs for active heart icons
    user_wishlist_ids = []
    if request.user.is_authenticated:
        from wishlist.models import WishlistItem
        user_wishlist_ids = list(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        'product': product,
        'variants': variants,
        'images': product.images.all(),
        'complete_the_style': complete_style,
        'more_like_this': more_like_this,
        'recommended_for_you': recommended_for_you,
        'related_products': more_like_this,
        'user_wishlist_ids': user_wishlist_ids,
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

def outfit_builder_view(request):
    """Interactive Mix & Match Studio page where users pair tops, bottoms, outerwear, footwear & accessories."""
    active_prods = Product.objects.filter(is_active=True).prefetch_related('images', 'variants', 'category')
    
    outers = []
    tops = []
    bottoms = []
    shoes = []
    accessories = []

    for p in active_prods:
        c_slug = p.category.slug.lower() if p.category else ''
        p_name = p.name.lower()
        
        img = p.primary_image
        img_url = img.image.url if (img and img.image) else 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600&auto=format&fit=crop&q=80'
        first_variant = p.variants.filter(is_active=True, stock_quantity__gt=0).first()
        variant_id = first_variant.id if first_variant else None
        
        item_data = {
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'brand': p.brand,
            'price': float(p.discounted_price),
            'original_price': float(p.base_price),
            'image_url': img_url,
            'variant_id': variant_id,
            'category_name': p.category.name if p.category else '',
        }
        
        if c_slug in ['jackets', 'hoodies']:
            outers.append(item_data)
        elif c_slug in ['denim'] or any(k in p_name for k in ['pant', 'trouser', 'short']):
            bottoms.append(item_data)
        elif c_slug in ['footwear']:
            shoes.append(item_data)
        elif c_slug in ['accessories']:
            accessories.append(item_data)
        elif c_slug in ['shirts', 'men'] or any(k in p_name for k in ['top', 'shirt', 'tee']):
            tops.append(item_data)
        else:
            tops.append(item_data)

    context = {
        'outers': outers,
        'tops': tops,
        'bottoms': bottoms,
        'shoes': shoes,
        'accessories': accessories,
    }
    return render(request, 'products/outfit_builder.html', context)

def api_pincode_check(request):
    """Checks Indian postal code validity, estimates delivery timelines, and COD status."""
    import re
    from datetime import datetime, timedelta

    pincode = request.GET.get('pincode', '').strip()
    if not pincode or not re.match(r'^[1-9][0-9]{5}$', pincode):
        return JsonResponse({
            'success': False,
            'message': 'Please enter a valid 6-digit Indian PIN code.'
        })

    prefix = pincode[:2]
    # Metro city identification
    metro_prefixes = {
        '11': 'New Delhi / NCR',
        '40': 'Mumbai',
        '56': 'Bengaluru',
        '60': 'Chennai',
        '70': 'Kolkata',
        '50': 'Hyderabad',
        '38': 'Ahmedabad',
        '41': 'Pune'
    }

    now = datetime.now()
    if prefix in metro_prefixes:
        city = metro_prefixes[prefix]
        delivery_days = 2
        delivery_date = now + timedelta(days=2)
        shipping_desc = f"Express Metro Courier to {city}"
    else:
        city = "Your City"
        delivery_days = 4
        delivery_date = now + timedelta(days=4)
        shipping_desc = f"Standard Insured Courier to {city}"

    formatted_date = delivery_date.strftime('%a, %d %b')

    return JsonResponse({
        'success': True,
        'pincode': pincode,
        'city': city,
        'delivery_date': formatted_date,
        'days': delivery_days,
        'description': shipping_desc,
        'cod_available': True,
        'free_shipping': True,
    })

