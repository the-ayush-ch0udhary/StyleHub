import os
import re
import json
import logging
import requests
from django.conf import settings
from .models import Product

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are "Aria", the Chief Fashion Stylist and Atelier Concierge for StyleHub, a contemporary luxury fashion house.
Your tone is sophisticated, discerning, warm, and sartorially expert (reminiscent of Savile Row tailors and high-end Milanese personal stylists).

CRITICAL GENDER-AWARE STYLING RULES:
1. Pay strict attention to the wearer's gender:
   - If the user states or implies they are a BOY, MAN, MALE, GUY, or GENTLEMAN:
     You MUST NEVER recommend dresses, skirts, slip dresses, wrap dresses, floral midi dresses, or items from the Women's Collection. Doing so is considered a critical error.
     Recommend exclusively tailored menswear or unisex pieces from the catalog: crisp Oxford cotton shirts, relaxed camp-collar linen shirts, heavy cotton boxy tees, heavyweight hoodies, classic denim jackets, selvedge Japanese denim, calfskin leather low-tops, or minimalist leather belts.
   - If the user states or implies they are a GIRL, WOMAN, FEMALE, LADY, or shopping for womenswear:
     Recommend elegant women's silhouettes: wrap dresses, silk charmeuse bias-cut slip dresses, floral midi dresses, high-waist wide-leg trousers, tailored overcoats, ribbed fitted tops.
   - If gender is unspecified, recommend universally flattering versatile essentials or ask a subtle styling preference.
2. Ground all recommendations exclusively in StyleHub's real catalog provided below. Never invent non-existent products.
3. Explain why the textures, tones, and silhouettes harmonize together for the occasion.
4. At the very end of your response, specify recommended products in this exact format on a new line:
[RECOMMENDED_PRODUCTS: id1, id2, ...]
where id1, id2 are the numeric product IDs from the catalog that match the wearer.

STYLEHUB CURRENT PRODUCT CATALOG:
{catalog_json}
"""

WOMEN_CATEGORIES = {"women's collection", "women", "womenswear"}
WOMEN_KEYWORDS = ["dress", "skirt", "slip dress", "wrap dress", "midi dress", "fitted top", "wide-leg trousers"]
MEN_CATEGORIES = {"men's apparel", "men", "menswear"}

def detect_gender(query):
    """
    Identifies gender intent from customer message.
    Returns 'male', 'female', or 'unspecified'.
    """
    q = f" {query.lower()} "
    male_patterns = [
        r'\b(boy|man|men|guy|guys|male|gentleman|gentlemen|groom|boyfriend|husband|father|son|brother)\b',
        r'\bmenswear\b', r'\bmen\'s\b', r'\bfor him\b'
    ]
    female_patterns = [
        r'\b(girl|girls|woman|women|female|lady|ladies|bride|girlfriend|wife|mother|daughter|sister)\b',
        r'\bwomenswear\b', r'\bwomen\'s\b', r'\bfor her\b'
    ]
    
    is_male = any(re.search(pat, q) for pat in male_patterns)
    is_female = any(re.search(pat, q) for pat in female_patterns)
    
    if is_male and not is_female:
        return 'male'
    if is_female and not is_male:
        return 'female'
    return 'unspecified'

def filter_catalog_by_gender(catalog, gender):
    """Filters catalog items to strictly prevent cross-gender recommendations."""
    if gender == 'male':
        filtered = []
        for p in catalog:
            cat = (p.get('category') or '').lower()
            name = (p.get('name') or '').lower()
            if cat in WOMEN_CATEGORIES or any(kw in name for kw in WOMEN_KEYWORDS):
                continue
            filtered.append(p)
        return filtered
    elif gender == 'female':
        filtered = []
        for p in catalog:
            cat = (p.get('category') or '').lower()
            if cat in MEN_CATEGORIES and not any(kw in p.get('name', '').lower() for kw in ['sneaker', 'belt', 'overcoat']):
                continue
            filtered.append(p)
        return filtered
    return catalog

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
    Attempts Google Gemini API (via fast native REST endpoint) first;
    gracefully falls back to local intelligent semantic agent.
    Strictly enforces gender-appropriate styling.
    """
    catalog = get_catalog_summary()
    catalog_by_id = {item['id']: item for item in catalog}
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')

    gender = detect_gender(user_message)
    # If not detected in current query, check previous user message
    if gender == 'unspecified' and conversation_history:
        for prev in reversed(conversation_history):
            if prev.get('role') == 'user':
                prev_gender = detect_gender(prev.get('text', ''))
                if prev_gender != 'unspecified':
                    gender = prev_gender
                    break

    gender_filtered_catalog = filter_catalog_by_gender(catalog, gender)
    gender_filtered_ids = {p['id'] for p in gender_filtered_catalog}

    ai_text = None
    recommended_ids = []
    engine_name = 'StyleHub Atelier AI Engine'

    # Attempt Live Google Gemini API if API key is present
    if api_key and api_key.strip():
        catalog_context = json.dumps([
            {
                'id': p['id'],
                'name': p['name'],
                'category': p['category'],
                'price': f"₹{p['price']}",
                'sizes': p['available_sizes'],
                'desc': p['description']
            }
            for p in gender_filtered_catalog
        ], indent=2)

        prompt = SYSTEM_PROMPT.format(catalog_json=catalog_context)
        if current_product_id and current_product_id in catalog_by_id:
            curr_p = catalog_by_id[current_product_id]
            prompt += f"\n\nContext: The customer is currently viewing Product ID {curr_p['id']}: '{curr_p['name']}' in {curr_p['category']} priced at ₹{curr_p['price']}."

        chat_parts = [prompt]
        if conversation_history:
            for msg in conversation_history[-4:]:
                prefix = "Customer: " if msg.get('role') == 'user' else "Aria: "
                chat_parts.append(f"{prefix}{msg.get('text', '')}")

        chat_parts.append(f"Customer: {user_message}")
        full_query = "\n\n".join(chat_parts)

        # Try gemini-2.5-flash first, then gemini-flash-latest
        models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.0-flash']
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": full_query}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                        "thinkingConfig": {
                            "thinkingBudget": 0
                        }
                    }
                }
                resp = requests.post(url, json=payload, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get('candidates', [])
                    if candidates and 'content' in candidates[0]:
                        parts = candidates[0]['content'].get('parts', [])
                        if parts and 'text' in parts[0]:
                            full_text = parts[0]['text']
                            # Parse recommended products
                            match = re.search(r'\[?RECOMMENDED_PRODUCTS:\s*([0-9,\s]+)\]?', full_text, re.IGNORECASE)
                            if match:
                                id_strs = match.group(1).split(',')
                                for s in id_strs:
                                    s_clean = s.strip()
                                    if s_clean.isdigit():
                                        recommended_ids.append(int(s_clean))
                                ai_text = re.sub(r'\[?RECOMMENDED_PRODUCTS:\s*([0-9,\s]+)\]?', '', full_text, flags=re.IGNORECASE).strip()
                            else:
                                ai_text = full_text.strip()
                            engine_name = f"Gemini 2.5 Flash ({model_name})"
                            break
                else:
                    logger.warning(f"Gemini API model {model_name} returned HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"Gemini model {model_name} failed: {e}")

    # Fallback to local intelligent stylist if Gemini didn't return text
    if not ai_text:
        ai_text, recommended_ids = _local_intelligent_fashion_agent(user_message, gender_filtered_catalog, current_product_id, gender)
        engine_name = 'StyleHub Atelier AI Engine'

    # Strict Safety Filter: Guarantee recommendations strictly match the wearer's gender
    safe_recommended_ids = [pid for pid in recommended_ids if pid in gender_filtered_ids]
    
    # If no valid IDs were returned by the AI, populate with top pieces from the filtered catalog
    if not safe_recommended_ids:
        safe_recommended_ids = [p['id'] for p in gender_filtered_catalog[:3]]

    # Resolve recommended product cards
    recommended_products = []
    for pid in safe_recommended_ids:
        if pid in catalog_by_id and catalog_by_id[pid] not in recommended_products:
            recommended_products.append(catalog_by_id[pid])

    # Cap to top 4 recommendations
    recommended_products = recommended_products[:4]

    return {
        'response': ai_text,
        'products': recommended_products,
        'engine': engine_name,
    }

def _local_intelligent_fashion_agent(query, catalog, current_product_id=None, gender='unspecified'):
    """
    High-fidelity offline AI styling engine.
    Understands intent (gender, sizing, occasions, color pairing, budget, material queries)
    and constructs nuanced luxury stylist feedback with exact catalog pairings.
    """
    q_lower = query.lower()
    recommended_ids = []
    catalog_by_id = {item['id']: item for item in catalog}

    # Sizing / Fit inquiry
    is_sizing = any(w in q_lower for w in ['size', 'fit', 'sizing', 'height', 'weight', 'kg', 'chest', 'waist', 'true to size', 'shrink', 'gsm'])
    if is_sizing:
        if current_product_id and current_product_id in catalog_by_id:
            p = catalog_by_id[current_product_id]
            text = (
                f"### Sartorial Fit Advisory: **{p['name']}**\n\n"
                f"Our garments are cut with modern architectural silhouettes in mind. Here is our tailoring guidance:\n\n"
                f"- **Fabric & Silhouette:** Engineered with high-density fabric ({'280 GSM combed jersey' if 'tee' in p['name'].lower() else 'heavyweight Japanese weave'}). It drapes naturally with a structured, relaxed profile rather than clinging.\n"
                f"- **Fit Profile:** Designed for a contemporary relaxed drop.\n"
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
            for p in catalog:
                if any(k in p['name'].lower() for k in ['denim', 'crewneck', 'sneaker']):
                    recommended_ids.append(p['id'])
        return text, recommended_ids

    # Date Night / Evening / Formal Occasion
    if any(w in q_lower for w in ['date', 'evening', 'party', 'dinner', 'cocktail', 'night out', 'formal', 'smart casual']):
        if gender == 'male':
            text = (
                "### Atelier Curated Look: **Refined Date Night Sophistication**\n\n"
                "For an elevated evening date, combine structured textures with relaxed tailoring to project effortless masculine confidence:\n\n"
                "1. **The Foundation:** Pair our **Relaxed Camp-Collar Linen Shirt** or **Classic Oxford Cotton Shirt** with dark tailored denim.\n"
                "2. **The Denim:** Our **14oz Japanese Selvedge Straight-Leg Denim** delivers a sharp, clean break above your footwear with zero artificial slouch.\n"
                "3. **The Layer:** Layer a structured **Classic Denim Jacket** or **Structured Wool-Blend Overcoat** for depth and tactile contrast.\n"
                "4. **Footwear & Accents:** Anchor the look with **Minimalist Calfskin Leather Low-Tops** and our **Full-Grain Bridle Leather Belt**."
            )
            for p in catalog:
                p_name = p['name'].lower()
                if any(k in p_name for k in ['linen shirt', 'selvedge', 'denim jacket', 'oxford', 'calfskin', 'belt']):
                    recommended_ids.append(p['id'])
        elif gender == 'female':
            text = (
                "### Atelier Curated Look: **Refined Evening Elegance**\n\n"
                "For an understated yet striking date night aesthetic, balance lustrous fluid drape with architectural layering:\n\n"
                "1. **The Statement:** The **Silk Charmeuse Bias-Cut Slip Dress** or **Elegant Wrap Dress** creates a timeless, luminous silhouette.\n"
                "2. **The Layer:** Throw a **Structured Wool-Blend Overcoat** across the shoulders for high-fashion Milanese contrast.\n"
                "3. **Modern Alternative:** Pair our **High-Waist Wide-Leg Trousers** with a **Ribbed Fitted Top** for contemporary, chic tailoring."
            )
            for p in catalog:
                p_name = p['name'].lower()
                if any(k in p_name for k in ['slip dress', 'wrap dress', 'wide-leg', 'overcoat', 'fitted top']):
                    recommended_ids.append(p['id'])
        else:
            text = (
                "### Atelier Curated Look: **Refined Evening Elegance**\n\n"
                "For an understated yet striking evening aesthetic, the key lies in juxtaposing rich tactile textures with clean, unadorned silhouettes:\n\n"
                "1. **The Foundation:** Pair deep, rich tones (such as our midnight selvedge or breathable linen) with tailored layering.\n"
                "2. **The Layer:** A structured overcoat or sharp camp-collar shirt elevates the outfit instantly without feeling overly stiff.\n"
                "3. **Footwear & Details:** Finish with handcrafted calfskin low-tops or minimalist leather accents to achieve effortless modern luxury."
            )
            for p in catalog:
                p_name = p['name'].lower()
                if any(k in p_name for k in ['overcoat', 'selvedge', 'linen shirt', 'low-top']):
                    recommended_ids.append(p['id'])
        return text, recommended_ids

    # Streetwear / Casual / Winter Layering
    if any(w in q_lower for w in ['streetwear', 'casual', 'winter', 'warm', 'hoodie', 'jacket', 'layer', 'cold']):
        text = (
            "### Atelier Curated Look: **Architectural Street Luxury**\n\n"
            "Layering demands tonal depth and graduated fabric weights. Here is our recommended capsule pairing:\n\n"
            "- **Base:** 280 GSM Boxy Crewneck T-Shirt as a breathable, ultra-soft foundation.\n"
            "- **Mid-Layer:** Heavyweight French Terry Hoodie or Classic Denim Jacket for tactile contrast.\n"
            "- **Bottoms:** 14oz Japanese shuttle-loom selvedge denim for a crisp, structured break above your sneakers."
        )
        for p in catalog:
            p_name = p['name'].lower()
            if any(k in p_name for k in ['hoodie', 'denim jacket', 'crewneck', 'japanese denim', 'urban']):
                recommended_ids.append(p['id'])
        return text, recommended_ids

    # Budget constraint
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

    # Material / Fabric specific queries
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
    for p in catalog:
        if p['discount_pct'] > 0 or p['category'] in ['Denim', 'Jackets & Outerwear', 'Shirts & Tops', "Men's Apparel"]:
            recommended_ids.append(p['id'])

    return text, recommended_ids
