from .models import Category

def categories_context(request):
    """Provides active categories to navbar and dropdowns."""
    categories = Category.objects.filter(is_active=True).order_by('name')
    return {
        'nav_categories': categories
    }
