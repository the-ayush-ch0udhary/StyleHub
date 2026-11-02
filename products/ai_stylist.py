import os
import re
import json
import logging
from django.conf import settings
from .models import Product, ProductVariant

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are "Aria", the Chief Fashion Stylist and Atelier Concierge for StyleHub, a contemporary luxury fashion house.
Your tone is sophisticated, discerning, warm, and sartorially expert (reminiscent of Savile Row tailors and high-end Milanese personal stylists).

Your goals:
1. Provide personalized outfit styling, silhouette guidance, and capsule wardrobe advice.
2. Answer sizing and fit inquiries accurately (e.g., advising on 280 GSM heavyweight cotton drape, boxy drop-shoulder fits, or raw selvedge denim breaks).
3. Ground all recommendations exclusively in StyleHub's real catalog provided below.
4. When suggesting items, explain *why* the textures, tones, and silhouettes harmonize together.
5. At the very end of your response, specify recommended products in this exact format on a new line:
[RECOMMENDED_PRODUCTS: id1, id2, ...]
where id1, id2 are the numeric product IDs from the catalog.

STYLEHUB CURRENT PRODUCT CATALOG:
{catalog_json}
"""

def get_catalog_summary():
    """Builds a structured dictionary of all available products for the AI model."""
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants')
    catalog = []
    for p in products:
        primary_img = p.primary_image
        img_url = primary_img.image.url if (primary_img and primary_img.image) else ''
        first_variant = p.variants.filter(is_active=True, stock_quantity__gt=0).first()
        sizes = list(p.variants.filter(is_active=True, stock_quantity__gt=0).values_list('size', flat=True).distinct())

        catalog.append({
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'category': p.category.name if p.category else 'General',
            'price': float(p.discounted_price),
            'original_price': float(p.base_price),
            'discount_pct': float(p.discount_percentage),
            'description': p.description[:180],
            'available_sizes': sizes,
            'image_url': img_url,
            'default_variant_id': first_variant.id if first_variant else None,
        })
    return catalog

def ask_ai_stylist(user_message, current_product_id=None, conversation_history=None):
    """
    Main entry point for the AI Stylist.
    Attempts Google Gemini API first; gracefully falls back to local intelligent semantic agent.
    """
    catalog = get_catalog_summary()
    catalog_by_id = {item['id']: item for item in catalog}
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')

    ai_text = None
    recommended_ids = []

    # Attempt Live Google Gemini API if API key is present
    if api_key and api_key.strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel('gemini-1.5-flash')

            catalog_context = json.dumps([
                {
                    'id': p['id'],
                    'name': p['name'],
                    'category': p['category'],
                    'price': f"₹{p['price']}",
                    'sizes': p['available_sizes'],
                    'desc': p['description']
                }
                for p in catalog
            ], indent=2)

            prompt = SYSTEM_PROMPT.format(catalog_json=catalog_context)
            if current_product_id and current_product_id in catalog_by_id:
                curr_p = catalog_by_id[current_product_id]
                prompt += f"\n\nContext: The customer is currently viewing Product ID {curr_p['id']}: '{curr_p['name']}' in {curr_p['category']} priced at ₹{curr_p['price']}."

            chat_messages = []
            if conversation_history:
                for msg in conversation_history[-6:]:
                    role = 'user' if msg.get('role') == 'user' else 'model'
                    chat_messages.append({'role': role, 'parts': [msg.get('text', '')]})

            chat_messages.append({'role': 'user', 'parts': [user_message]})
            response = model.generate_content([prompt] + [m['parts'][0] for m in chat_messages])

            if response and response.text:
                full_text = response.text
                match = re.search(r'\[RECOMMENDED_PRODUCTS:\s*([0-9,\s]+)\]', full_text)
                if match:
                    id_strs = match.group(1).split(',')
                    for s in id_strs:
                        s_clean = s.strip()
                        if s_clean.isdigit():
                            recommended_ids.append(int(s_clean))
                    ai_text = re.sub(r'\[RECOMMENDED_PRODUCTS:\s*([0-9,\s]+)\]', '', full_text).strip()
                else:
                    ai_text = full_text.strip()
        except Exception as e:
            logger.warning(f"Gemini API request failed, engaging local AI agent fallback: {e}")
            ai_text = None

    # Intelligent Local Rule & Semantic Matcher Fallback
    if not ai_text:
        ai_text, recommended_ids = _local_intelligent_fashion_agent(user_message, catalog, current_product_id)

    # Resolve recommended product cards
    recommended_products = []
    for pid in recommended_ids:
        if pid in catalog_by_id and catalog_by_id[pid] not in recommended_products:
            recommended_products.append(catalog_by_id[pid])

    # Cap to top 4 recommendations
    recommended_products = recommended_products[:4]

    return {
        'response': ai_text,
        'products': recommended_products,
        'engine': 'Gemini 1.5 Flash' if (api_key and ai_text and 'Gemini' in str(type(api_key))) else 'StyleHub Atelier AI Engine',
    }

def _local_intelligent_fashion_agent(query, catalog, current_product_id=None):
    """
    High-fidelity offline AI styling engine.
    Understands intent (sizing, occasions, color pairing, budget, material queries)
    and constructs nuanced luxury stylist feedback with exact catalog pairings.
    """
    q_lower = query.lower()
    recommended_ids = []

    # Map categories and archetypes
    catalog_by_id = {item['id']: item for item in catalog}
    
    # Check for Sizing / Fit inquiry
    is_sizing = any(w in q_lower for w in ['size', 'fit', 'sizing', 'height', 'weight', 'kg', 'chest', 'waist', 'true to size', 'shrink', 'gsm'])
    if is_sizing:
        if current_product_id and current_product_id in catalog_by_id:
            p = catalog_by_id[current_product_id]
            text = (
                f"### Sartorial Fit Advisory: **{p['name']}**\n\n"
                f"Our garments are cut with modern architectural silhouettes in mind. Here is our tailoring guidance:\n\n"
                f"- **Fabric & Silhouette:** Engineered with high-density fabric ({'280 GSM combed jersey' if 'tee' in p['name'].lower() else 'heavyweight Japanese weave'}). It drapes naturally with a structured, relaxed profile rather than clinging.\n"
                f"- **Fit Profile:** Designed for a slightly relaxed, contemporary streetwear drop.\n"
                f"- **Recommendation:** If you prefer the signature boxy, structured look, we strongly advise taking **your true size**. If you desire a tailored, closer-to-body contour, choose **one size down**.\n\n"
                f"*Available Sizes in stock:* {', '.join(p['available_sizes']) if p['available_sizes'] else 'Standard S, M, L, XL'}"
            )
            recommended_ids.append(p['id'])
        else:
            text = (
                "### StyleHub Fit & Sizing Guide\n\n"
                "Our capsule collections feature tailored boxy silhouettes with dropped shoulders and micro-adjusted waistbands:\n\n"
                "- **Tees & Hoodies:** Cut true-to-size for a relaxed, heavyweight drape (no cling). Choose your standard size for the intended designer silhouette.\n"
                "- **Japanese Selvedge Denim:** Straight-leg cut with zero synthetic stretch. We recommend measuring your actual waistline or staying true to size.\n"
                "- **Footwear:** Minimalist calfskin sneakers fit true to standard European / UK sizing."
            )
            # Recommend versatile essentials
            for p in catalog:
                if any(k in p['name'].lower() for k in ['denim', 'crewneck', 'sneaker']):
                    recommended_ids.append(p['id'])
        return text, recommended_ids

    # Check for Date Night / Evening / Formal Occasion
    if any(w in q_lower for w in ['date', 'evening', 'party', 'dinner', 'cocktail', 'night out', 'formal', 'smart casual']):
        text = (
            "### Atelier Curated Look: **Refined Evening Elegance**\n\n"
            "For an understated yet striking evening aesthetic, the key lies in juxtaposing rich tactile textures with clean, unadorned silhouettes:\n\n"
            "1. **The Foundation:** Pair deep, rich tones (such as our midnight selvedge or lustrous bias-cut slip dress) with tailored layering.\n"
            "2. **The Layer:** A structured overcoat or sharp camp-collar shirt elevates the outfit instantly without feeling overly stiff.\n"
            "3. **Footwear & Details:** Finish with handcrafted calfskin low-tops or minimalist leather accents to achieve effortless modern luxury."
        )
        # Select matching items
        for p in catalog:
            p_name = p['name'].lower()
            if any(k in p_name for k in ['overcoat', 'slip dress', 'selvedge', 'linen shirt', 'low-top']):
                recommended_ids.append(p['id'])
        return text, recommended_ids

    # Check for Streetwear / Casual / Winter Layering
    if any(w in q_lower for w in ['streetwear', 'casual', 'winter', 'warm', 'hoodie', 'jacket', 'layer', 'cold']):
        text = (
            "### Atelier Curated Look: **Architectural Street Luxury**\n\n"
            "Winter dressing demands tonal depth and graduated fabric weights. Here is our recommended capsule pairing:\n\n"
            "- **Base:** 280 GSM Boxy Crewneck T-Shirt as a breathable, ultra-soft foundation.\n"
            "- **Mid-Layer:** Heavyweight French Terry Hoodie or Classic Denim Jacket for tactile contrast.\n"
            "- **Bottoms:** 14oz Japanese shuttle-loom selvedge denim for a crisp, structured break above your sneakers."
        )
        for p in catalog:
            p_name = p['name'].lower()
            if any(k in p_name for k in ['hoodie', 'denim jacket', 'crewneck', 'japanese denim', 'urban']):
                recommended_ids.append(p['id'])
        return text, recommended_ids

    # Check for Budget constraint (e.g., under 3000, 4000, 5000)
    budget_match = re.search(r'(?:under|below|less than|within)\s*(?:rs\.?|inr|₹)?\s*(\d+)', q_lower)
    if budget_match:
        max_b = float(budget_match.group(1))
        matching_prods = [p for p in catalog if p['price'] <= max_b]
        if matching_prods:
            matching_prods.sort(key=lambda x: x['price'], reverse=True)
            text = (
                f"### Curated Designer Selections Under ₹{int(max_b):,}\n\n"
                f"We have curated our finest investment pieces that deliver maximum cost-per-wear value while staying within your budget of ₹{int(max_b):,}. "
                f"Every item features our signature premium textiles and reinforced tailoring."
            )
            recommended_ids = [p['id'] for p in matching_prods[:4]]
            return text, recommended_ids

    # Material / Fabric specific queries (e.g. linen, silk, leather, denim, cotton)
    for mat in ['linen', 'silk', 'leather', 'denim', 'cotton', 'wool']:
        if mat in q_lower:
            text = (
                f"### Focus on Craftsmanship: **StyleHub {mat.capitalize()} Editions**\n\n"
                f"Our {mat} pieces are sourced directly from premier heritage fabric mills. "
                f"We celebrate raw texture, natural breathability, and garments engineered to develop a beautiful individual patina with wear."
            )
            for p in catalog:
                if mat in p['name'].lower() or mat in p['description'].lower():
                    recommended_ids.append(p['id'])
            if recommended_ids:
                return text, recommended_ids

    # Default versatile styling response
    text = (
        "### StyleHub Atelier Consultation\n\n"
        "Welcome to the StyleHub styling suite. Our philosophy centers on **timeless modular wardrobes**—minimal silhouettes, dropped shoulders, and museum-grade fabric density.\n\n"
        "Here are our most celebrated wardrobe foundation pieces currently available in the atelier. "
        "Feel free to ask for specific occasion styling, color harmonization, or personalized size advice!"
    )
    # Return featured / bestselling items
    for p in catalog:
        if p['discount_pct'] > 0 or p['category'] in ['Denim', 'Jackets', 'Shirts']:
            recommended_ids.append(p['id'])

    return text, recommended_ids

