from django.core.cache import cache
from .models import Category

def categories_context(request):
    """Provides active categories to navbar and dropdowns with caching."""
    categories = cache.get('nav_active_categories')
    if categories is None:
        categories = list(Category.objects.filter(is_active=True).order_by('name'))
        cache.set('nav_active_categories', categories, 3600)
    return {
        'nav_categories': categories
    }
