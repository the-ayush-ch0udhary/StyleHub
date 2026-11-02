# StyleHub - Luxury Fashion E-Commerce Platform

**StyleHub** is a modern, full-featured luxury fashion e-commerce platform built with Django 5, PostgreSQL, Razorpay, and Google Gemini AI. Designed for a sleek shopping experience, it delivers end-to-end e-commerce capabilities—from variant-based catalog browsing and AI-powered personal styling to secure payment processing and operational analytics.

---

## 🌐 Live Deployment

- **Live Storefront**: [https://stylehub-9ljl.onrender.com/](https://stylehub-9ljl.onrender.com/)
- **Admin Portal**: [https://stylehub-9ljl.onrender.com/admin/](https://stylehub-9ljl.onrender.com/admin/)

---
## Key Features

### 🤖 Artificial Intelligence & Personal Concierge
- **Atelier AI Stylist ("Aria")**: Interactive personal fashion consultant powered by Google Gemini 1.5 Flash with a zero-downtime offline semantic fallback engine.
- **Contextual Outfit Recommendations**: Suggests matching garments grounded exclusively in StyleHub's live catalog with interactive cards and 1-click *"Add to Bag"*.
- **Smart Sizing & Fit Advisor**: Delivers personalized fit guidance based on garment weight (e.g. 280 GSM cotton jersey, 14oz raw Japanese selvedge) and customer build.
- **Natural Language Product Discovery**: Understands occasion requests (e.g., *"monochrome evening cocktail look"* or *"breathable summer linen"*).

### 🛍️ Storefront & Shopping Experience
- **Luxury Product Catalog**: Categorized collections, multi-image galleries, and dynamic filtering.
- **Outfit Studio (Mix & Match)**: Interactive wardrobe builder allowing customers to pair tops, bottoms, outerwear, footwear, and accessories with complete bundle discounts.
- **Product Variants**: Independent SKU management for clothing sizes (S, M, L, XL) and color variants with real-time stock tracking.
- **Interactive Cart & Wishlist**: Slide-out AJAX cart drawer, item quantity updates, and a one-click "Move All to Bag" wishlist action.
- **Customer Reviews**: Verified customer reviews with 5-star rating breakdowns.

### 💳 Checkout, Coupons & Payments
- **Razorpay Payment Gateway**: Seamless checkout with card, UPI, and net-banking integration.
- **Webhook Processing**: HMAC-SHA256 signature verification for instant payment confirmation.
- **Automated Refunds**: Instant Razorpay refund initiation upon order cancellation.
- **Promotion & Coupons**: Fixed and percentage-based discounts with expiration dates and per-user usage limits.
- **PDF Invoices**: Printable order receipts and downloadable purchase summaries.

### 📊 Management & Administration
- **Executive Analytics Dashboard**: Real-time sales overview, revenue charts, order counts, and top-performing products.
- **Themed Admin Portal**: Customized Django Admin powered by Jazzmin with dark luxury aesthetics.
- **Asynchronous Notifications**: Background email and SMS dispatches for order confirmations and status changes.

---

## Tech Stack

- **Backend**: Python 3.12 / 3.14, Django 5
- **Artificial Intelligence**: Google Gemini 1.5 Flash (`google-generativeai`), Hybrid Semantic Fallback Engine
- **Database**: PostgreSQL (Neon Cloud / Serverless) or SQLite for local testing
- **Frontend**: HTML5, Vanilla CSS / Bootstrap 5, JavaScript (ES6+), FontAwesome, Bootstrap Icons
- **Static & Media**: WhiteNoise (compressed static asset serving), Pillow
- **Deployment**: Gunicorn (multi-threaded workers), Render.com

---

## Getting Started Locally

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/the-ayush-ch0udhary/StyleHub.git
cd StyleHub

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # On Windows
# source venv/bin/activate  # On Linux/macOS
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```ini
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database Configuration (defaults to SQLite if omitted)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# AI Stylist (Optional: free key from https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key

# Payment Gateway
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
```

### 4. Run Migrations & Seed Demo Data
```bash
python manage.py migrate
python manage.py seed_data
```

### 5. Start Development Server
```bash
python manage.py runserver
```
Visit **`http://127.0.0.1:8000/`** in your browser.

---

## Default Demo Credentials

| Role | Username | Password | Access URL |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin1234` | `/admin/` & `/dashboard/` |
| **Customer** | `john_doe` | `password123` | `/accounts/login/` |
