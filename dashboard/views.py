import json
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from orders.models import Order, OrderItem
from products.models import Product, ProductVariant, Category

STATUS_COLOR_MAP = {
    'PENDING': '#F59E0B',          # Amber
    'CONFIRMED': '#3B82F6',        # Blue
    'PROCESSING': '#8B5CF6',       # Purple
    'SHIPPED': '#06B6D4',          # Cyan
    'OUT_FOR_DELIVERY': '#EC4899',   # Pink
    'DELIVERED': '#10B981',        # Emerald Green
    'CANCELLED': '#EF4444',        # Crimson Red
}

@staff_member_required
def dashboard_view(request):
    # Quick Order Status Update action
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('new_status')
        tracking_number = request.POST.get('tracking_number')
        if order_id and new_status:
            order = get_object_or_404(Order, id=order_id)
            order.status = new_status
            if tracking_number is not None:
                order.tracking_number = tracking_number.strip()
            if new_status == 'DELIVERED' and order.payment_method == 'COD':
                order.payment_status = 'PAID'
            order.save()
            messages.success(request, f"Order #{order.order_number} status updated to {order.get_status_display()}.")
            return redirect('dashboard:index')

    now = timezone.now()

    # KPI Metrics
    paid_orders_qs = Order.objects.filter(payment_status='PAID')
    total_revenue_val = paid_orders_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_orders = Order.objects.count()
    paid_orders_count = paid_orders_qs.count()
    avg_order_value = (total_revenue_val / paid_orders_count) if paid_orders_count > 0 else Decimal('0.00')

    total_customers = User.objects.filter(is_staff=False).count()
    pending_orders = Order.objects.filter(status__in=['PENDING', 'CONFIRMED', 'PROCESSING']).count()
    delivered_orders = Order.objects.filter(status='DELIVERED').count()
    failed_payments = Order.objects.filter(payment_status='FAILED').count()
    total_products = Product.objects.filter(is_active=True).count()
    low_stock_variants_count = ProductVariant.objects.filter(is_active=True, stock_quantity__lte=5).count()

    # Low Stock Products (Variant stock <= 5)
    low_stock_variants = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity__lte=5
    ).select_related('product', 'product__category').order_by('stock_quantity', 'product__name')[:15]

    # Top Selling Products (by total revenue & quantity)
    top_selling_items = OrderItem.objects.filter(
        order__payment_status='PAID'
    ).values('product_name', 'sku').annotate(
        total_qty=Sum('quantity'),
        total_sales=Sum('subtotal')
    ).order_by('-total_sales')[:6]

    # Recent Orders (latest 15)
    recent_orders = Order.objects.select_related('user').prefetch_related('items')[:15]

    # 1. Orders by Status (Donut Chart)
    status_counts_raw = Order.objects.values('status').annotate(count=Count('id')).order_by('-count')
    status_dict_labels = dict(Order.STATUS_CHOICES)
    status_labels = []
    status_data = []
    status_colors = []
    for item in status_counts_raw:
        st_code = item['status']
        status_labels.append(status_dict_labels.get(st_code, st_code))
        status_data.append(item['count'])
        status_colors.append(STATUS_COLOR_MAP.get(st_code, '#64748B'))

    # 2. Sales by Category (Bar Chart)
    category_sales_raw = OrderItem.objects.filter(
        order__payment_status='PAID',
        variant__product__category__isnull=False
    ).values('variant__product__category__name').annotate(
        revenue=Sum('subtotal'),
        units=Sum('quantity')
    ).order_by('-revenue')[:8]

    cat_labels = [item['variant__product__category__name'] for item in category_sales_raw]
    cat_revenues = [float(item['revenue']) for item in category_sales_raw]
    cat_units = [item['units'] for item in category_sales_raw]

    # Fallback if no categorized sales yet
    if not cat_labels:
        active_categories = Category.objects.filter(is_active=True)[:6]
        cat_labels = [c.name for c in active_categories] or ["Men's Apparel", "Women's Collection", "Denim & Jeans", "Jackets & Outerwear"]
        cat_revenues = [0.0] * len(cat_labels)
        cat_units = [0] * len(cat_labels)

    # 3. Monthly Trend (Past 6 Months Continuous Timeline)
    months_dict = {}
    for i in range(5, -1, -1):
        m_date = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        key = m_date.strftime('%Y-%m')
        label = m_date.strftime('%b %Y')
        months_dict[key] = {'label': label, 'revenue': 0.0, 'orders': 0}

    start_6m = (now.replace(day=1) - timedelta(days=5 * 30)).replace(day=1)
    monthly_trend_qs = Order.objects.filter(
        payment_status='PAID',
        created_at__gte=start_6m
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        rev=Sum('total_amount'),
        cnt=Count('id')
    ).order_by('month')

    for item in monthly_trend_qs:
        if item['month']:
            k = item['month'].strftime('%Y-%m')
            if k in months_dict:
                months_dict[k]['revenue'] = float(item['rev'] or 0)
                months_dict[k]['orders'] = item['cnt']

    months_labels = [v['label'] for v in months_dict.values()]
    months_revenue = [v['revenue'] for v in months_dict.values()]
    months_orders = [v['orders'] for v in months_dict.values()]

    # 4. Daily Trend (Past 30 Days Continuous Timeline)
    daily_dict = {}
    for i in range(29, -1, -1):
        d_date = (now - timedelta(days=i)).date()
        key = d_date.strftime('%Y-%m-%d')
        label = d_date.strftime('%b %d')
        daily_dict[key] = {'label': label, 'revenue': 0.0, 'orders': 0}

    start_30d = now - timedelta(days=30)
    daily_trend_qs = Order.objects.filter(
        payment_status='PAID',
        created_at__gte=start_30d
    ).annotate(
        day=TruncDate('created_at')
    ).values('day').annotate(
        rev=Sum('total_amount'),
        cnt=Count('id')
    ).order_by('day')

    for item in daily_trend_qs:
        if item['day']:
            k = item['day'].strftime('%Y-%m-%d')
            if k in daily_dict:
                daily_dict[k]['revenue'] = float(item['rev'] or 0)
                daily_dict[k]['orders'] = item['cnt']

    daily_labels = [v['label'] for v in daily_dict.values()]
    daily_revenue = [v['revenue'] for v in daily_dict.values()]
    daily_orders = [v['orders'] for v in daily_dict.values()]

    # 5. Payment Methods Breakdown
    pm_qs = Order.objects.values('payment_method').annotate(
        count=Count('id'),
        rev=Sum('total_amount')
    )
    pm_map = dict(Order.PAYMENT_METHOD_CHOICES)
    pm_labels = []
    pm_data = []
    pm_rev_data = []
    pm_colors = []
    pm_color_map = {
        'RAZORPAY': '#6366F1',  # Indigo
        'COD': '#10B981',       # Emerald Green
    }
    for item in pm_qs:
        code = item['payment_method']
        pm_labels.append(pm_map.get(code, code))
        pm_data.append(item['count'])
        pm_rev_data.append(float(item['rev'] or 0))
        pm_colors.append(pm_color_map.get(code, '#3B82F6'))

    chart_payload = {
        'status_labels': status_labels,
        'status_data': status_data,
        'status_colors': status_colors,
        'cat_labels': cat_labels,
        'cat_revenues': cat_revenues,
        'cat_units': cat_units,
        'months_labels': months_labels,
        'months_revenue': months_revenue,
        'months_orders': months_orders,
        'daily_labels': daily_labels,
        'daily_revenue': daily_revenue,
        'daily_orders': daily_orders,
        'pm_labels': pm_labels,
        'pm_data': pm_data,
        'pm_rev_data': pm_rev_data,
        'pm_colors': pm_colors,
    }

    context = {
        'total_revenue': total_revenue_val,
        'total_orders': total_orders,
        'paid_orders_count': paid_orders_count,
        'avg_order_value': avg_order_value,
        'total_customers': total_customers,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'failed_payments': failed_payments,
        'total_products': total_products,
        'low_stock_variants_count': low_stock_variants_count,
        'low_stock_variants': low_stock_variants,
        'top_selling_items': top_selling_items,
        'recent_orders': recent_orders,
        'status_choices': Order.STATUS_CHOICES,
        'chart_payload_json': json.dumps(chart_payload),
    }
    return render(request, 'dashboard/index.html', context)

