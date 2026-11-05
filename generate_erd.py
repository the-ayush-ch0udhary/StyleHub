import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_chen_erd(output_png='STYLEHUB_ER_Diagram.png', output_pdf='STYLEHUB_ER_Diagram.pdf', output_svg='STYLEHUB_ER_Diagram.svg'):
    fig = plt.figure(figsize=(26, 16), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(-2.0, 26.0)
    ax.set_ylim(-0.5, 15.5)
    ax.axis('off')

    # Color palette - classic clean Chen notation matching PDF page 9
    border_color = '#111827'
    bg_color = '#FFFFFF'
    text_color = '#111827'
    line_color = '#374151'
    cardinality_color = '#1F2937'

    # Title
    ax.text(12.0, 14.8, 'STYLEHUB - Entity-Relationship (ER) Diagram', 
            fontsize=20, fontweight='bold', ha='center', va='center', family='sans-serif', color=text_color)
    ax.text(12.0, 14.3, 'Complete Chen-Notation Architecture (Derived from Django Models & SQLite / PostgreSQL Schema)', 
            fontsize=12, fontstyle='italic', ha='center', va='center', family='sans-serif', color='#4B5563')

    # Helper: Entity Rectangle
    def draw_entity(x, y, name, w=2.4, h=0.85):
        rect = patches.Rectangle((x - w/2, y - h/2), w, h, 
                                 linewidth=1.8, edgecolor=border_color, facecolor=bg_color, zorder=3)
        ax.add_patch(rect)
        ax.text(x, y, name, fontsize=10.0, fontweight='bold', ha='center', va='center', 
                family='sans-serif', color=text_color, zorder=4)
        return (x, y)

    # Helper: Relationship (Diamond)
    def draw_diamond(x, y, name, w=1.6, h=0.8):
        pts = [(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)]
        diamond = patches.Polygon(pts, linewidth=1.4, edgecolor=border_color, facecolor=bg_color, zorder=3)
        ax.add_patch(diamond)
        ax.text(x, y, name, fontsize=8.5, fontstyle='italic', ha='center', va='center', 
                family='sans-serif', color=text_color, zorder=4)
        return (x, y)

    # Helper: Attribute (Ellipse)
    def draw_attribute(x, y, name, is_pk=False, w=1.6, h=0.55):
        ellipse = patches.Ellipse((x, y), width=w, height=h,
                                  linewidth=1.0, edgecolor=border_color, facecolor=bg_color, zorder=3)
        ax.add_patch(ellipse)
        ax.text(x, y, name, fontsize=8.0, ha='center', va='center', 
                family='sans-serif', color=text_color, zorder=4)
        if is_pk:
            txt_len = len(name) * 0.046
            ax.plot([x - txt_len, x + txt_len], [y - 0.13, y - 0.13], color=text_color, lw=1.2, zorder=5)
        return (x, y)

    # Helper: Connect with Cardinality
    def connect(p1, p2, label=None, label_side='start', offset=0.3):
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=line_color, lw=1.2, zorder=2)
        if label:
            if label_side == 'start':
                lx = p1[0] + (p2[0] - p1[0]) * offset
                ly = p1[1] + (p2[1] - p1[1]) * offset + 0.16
            else:
                lx = p2[0] - (p2[0] - p1[0]) * offset
                ly = p2[1] - (p2[1] - p1[1]) * offset + 0.16
            ax.text(lx, ly, label, fontsize=9.5, fontweight='bold', ha='center', va='center', 
                    family='sans-serif', color=cardinality_color, zorder=4)

    # -------------------------------------------------------------
    # 1. ENTITY DEFINITIONS & PLACEMENT
    # -------------------------------------------------------------
    # Top Row (Y = 11.2)
    c_contact = draw_entity(-0.4, 11.2, 'CONTACT_MESSAGE', w=2.4, h=0.85)
    c_user = draw_entity(4.8, 11.2, 'USER\n(Customer/Admin)', w=2.4, h=0.9)
    c_order = draw_entity(12.0, 11.2, 'ORDER', w=2.2, h=0.85)
    c_order_item = draw_entity(18.5, 11.2, 'ORDER_ITEM', w=2.2, h=0.85)
    c_prod_img = draw_entity(24.0, 11.2, 'PRODUCT_IMAGE', w=2.2, h=0.85)

    # Middle Row (Y = 6.8)
    c_cart = draw_entity(4.8, 6.8, 'CART', w=2.2, h=0.85)
    c_payment = draw_entity(12.0, 6.8, 'PAYMENT', w=2.2, h=0.85)
    c_prod_var = draw_entity(18.5, 6.8, 'PRODUCT_VARIANT', w=2.4, h=0.85)
    c_product = draw_entity(24.0, 6.8, 'PRODUCT', w=2.2, h=0.85)

    # Bottom Row (Y = 2.2)
    c_cart_item = draw_entity(4.8, 2.2, 'CART_ITEM', w=2.2, h=0.85)
    c_coupon = draw_entity(12.0, 2.2, 'COUPON', w=2.2, h=0.85)
    c_review = draw_entity(18.5, 2.2, 'REVIEW', w=2.2, h=0.85)
    c_category = draw_entity(24.0, 2.2, 'CATEGORY', w=2.2, h=0.85)

    # -------------------------------------------------------------
    # 2. RELATIONSHIPS (DIAMONDS) & CONNECTORS
    # -------------------------------------------------------------
    # USER --- Submits [1:N] ---> CONTACT_MESSAGE
    r_submits = draw_diamond(2.2, 11.2, 'Submits', w=1.5, h=0.75)
    connect(c_user, r_submits, '1', 'start', 0.4)
    connect(r_submits, c_contact, 'N', 'end', 0.4)

    # USER --- Places [1:N] ---> ORDER
    r_places = draw_diamond(8.4, 11.2, 'Places', w=1.5, h=0.75)
    connect(c_user, r_places, '1', 'start', 0.4)
    connect(r_places, c_order, 'N', 'end', 0.4)

    # ORDER --- Contains [1:N] ---> ORDER_ITEM
    r_contains_order = draw_diamond(15.25, 11.2, 'Contains', w=1.5, h=0.75)
    connect(c_order, r_contains_order, '1', 'start', 0.4)
    connect(r_contains_order, c_order_item, 'N', 'end', 0.4)

    # USER --- Owns [1:1] ---> CART
    r_owns = draw_diamond(4.8, 9.0, 'Owns', w=1.4, h=0.75)
    connect(c_user, r_owns, '1', 'start', 0.4)
    connect(r_owns, c_cart, '1', 'end', 0.4)

    # CART --- Contains [1:M] ---> CART_ITEM
    r_contains_cart = draw_diamond(4.8, 4.5, 'Contains', w=1.5, h=0.75)
    connect(c_cart, r_contains_cart, '1', 'start', 0.4)
    connect(r_contains_cart, c_cart_item, 'M', 'end', 0.4)

    # ORDER --- Has [1:1] ---> PAYMENT
    r_has_pay = draw_diamond(12.0, 9.0, 'Has', w=1.4, h=0.75)
    connect(c_order, r_has_pay, '1', 'start', 0.4)
    connect(r_has_pay, c_payment, '1', 'end', 0.4)

    # PAYMENT --- Applies [N:1] ---> COUPON
    r_applies = draw_diamond(12.0, 4.5, 'Applies', w=1.4, h=0.75)
    connect(c_payment, r_applies, 'N', 'start', 0.4)
    connect(r_applies, c_coupon, '1', 'end', 0.4)

    # ORDER_ITEM --- References [N:1] ---> PRODUCT_VARIANT
    r_item_ref = draw_diamond(18.5, 9.0, 'References', w=1.6, h=0.75)
    connect(c_order_item, r_item_ref, 'N', 'start', 0.4)
    connect(r_item_ref, c_prod_var, '1', 'end', 0.4)

    # PRODUCT_VARIANT --- Variant of [N:1] ---> PRODUCT
    r_var_of = draw_diamond(21.25, 6.8, 'Variant of', w=1.6, h=0.75)
    connect(c_prod_var, r_var_of, 'N', 'start', 0.4)
    connect(r_var_of, c_product, '1', 'end', 0.4)

    # PRODUCT --- Displays [1:N] ---> PRODUCT_IMAGE
    r_displays = draw_diamond(24.0, 9.0, 'Displays', w=1.5, h=0.75)
    connect(c_product, r_displays, '1', 'start', 0.4)
    connect(r_displays, c_prod_img, 'N', 'end', 0.4)

    # PRODUCT --- Belongs to [N:1] ---> CATEGORY
    r_belongs = draw_diamond(24.0, 4.5, 'Belongs to', w=1.6, h=0.75)
    connect(c_product, r_belongs, 'N', 'start', 0.4)
    connect(r_belongs, c_category, '1', 'end', 0.4)

    # CATEGORY --- Has [1:N] ---> REVIEW (as in PDF page 9)
    r_has_rev = draw_diamond(21.25, 2.2, 'Has', w=1.4, h=0.75)
    connect(c_category, r_has_rev, '1', 'start', 0.4)
    connect(r_has_rev, c_review, 'N', 'end', 0.4)

    # -------------------------------------------------------------
    # 3. ATTRIBUTE ELLIPSES (WITH UNDERLINED PRIMARY KEYS)
    # -------------------------------------------------------------
    # CONTACT_MESSAGE Attributes
    cm_attrs = [
        (-0.4, 12.8, 'message_id', True),
        (-1.2, 12.0, 'name', False),
        (-1.2, 10.4, 'email', False),
        (-0.4, 9.8, 'subject', False),
    ]
    for ax_pos, ay_pos, name, is_pk in cm_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_contact[0], ax_pos], [c_contact[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # USER Attributes
    u_attrs = [
        (3.3, 12.8, 'user_id', True),
        (4.8, 13.0, 'username', False),
        (6.3, 12.8, 'email', False),
        (3.2, 11.9, 'first_name', False),
        (6.4, 11.9, 'last_name', False),
        (3.2, 10.4, 'password', False),
        (6.4, 10.4, 'date_joined', False),
    ]
    for ax_pos, ay_pos, name, is_pk in u_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_user[0], ax_pos], [c_user[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # ORDER Attributes
    o_attrs = [
        (10.5, 12.8, 'order_id', True),
        (12.0, 13.0, 'order_number', False),
        (13.5, 12.8, 'status', False),
        (9.8, 12.0, 'payment_method', False),
        (14.2, 12.0, 'razorpay_order_id', False),
        (10.0, 10.4, 'total_amount', False),
    ]
    for ax_pos, ay_pos, name, is_pk in o_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_order[0], ax_pos], [c_order[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # ORDER_ITEM Attributes
    oi_attrs = [
        (17.2, 12.8, 'order_item_id', True),
        (18.5, 13.0, 'product_name', False),
        (19.8, 12.8, 'size / color', False),
        (16.8, 12.0, 'quantity', False),
        (20.2, 12.0, 'unit_price', False),
    ]
    for ax_pos, ay_pos, name, is_pk in oi_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_order_item[0], ax_pos], [c_order_item[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # PRODUCT_IMAGE Attributes
    pi_attrs = [
        (22.6, 12.8, 'image_id', True),
        (24.0, 13.0, 'image_url', False),
        (25.4, 12.8, 'is_primary', False),
        (25.4, 11.9, 'alt_text', False),
    ]
    for ax_pos, ay_pos, name, is_pk in pi_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_prod_img[0], ax_pos], [c_prod_img[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # CART Attributes
    cart_attrs = [
        (3.0, 7.6, 'cart_id', True),
        (3.0, 6.2, 'session_key', False),
        (6.5, 7.6, 'created_at', False),
        (6.5, 6.2, 'updated_at', False),
    ]
    for ax_pos, ay_pos, name, is_pk in cart_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_cart[0], ax_pos], [c_cart[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # PAYMENT Attributes
    pay_attrs = [
        (10.2, 7.6, 'payment_id', True),
        (9.8, 6.2, 'razorpay_pay_id', False),
        (13.8, 7.6, 'status', False),
        (14.0, 6.2, 'amount', False),
        (10.2, 5.4, 'payment_date', False),
    ]
    for ax_pos, ay_pos, name, is_pk in pay_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_payment[0], ax_pos], [c_payment[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # PRODUCT_VARIANT Attributes
    pv_attrs = [
        (16.8, 7.6, 'variant_id', True),
        (16.5, 6.2, 'sku', False),
        (17.2, 5.6, 'size', False),
        (18.5, 5.4, 'color / hex', False),
        (19.8, 5.6, 'stock_quantity', False),
    ]
    for ax_pos, ay_pos, name, is_pk in pv_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_prod_var[0], ax_pos], [c_prod_var[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # PRODUCT Attributes
    p_attrs = [
        (22.6, 7.8, 'product_id', True),
        (25.4, 7.8, 'name', False),
        (25.4, 6.8, 'brand', False),
        (25.4, 5.8, 'base_price', False),
        (24.0, 5.4, 'discount_pct', False),
        (22.6, 5.6, 'description', False),
    ]
    for ax_pos, ay_pos, name, is_pk in p_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_product[0], ax_pos], [c_product[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # CART_ITEM Attributes
    ci_attrs = [
        (3.0, 2.8, 'cart_item_id', True),
        (3.0, 1.6, 'quantity', False),
        (4.8, 1.0, 'created_at', False),
    ]
    for ax_pos, ay_pos, name, is_pk in ci_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_cart_item[0], ax_pos], [c_cart_item[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # COUPON Attributes
    coup_attrs = [
        (10.2, 2.8, 'coupon_id', True),
        (10.2, 1.6, 'code', False),
        (12.0, 1.0, 'discount_type', False),
        (13.8, 2.8, 'discount_value', False),
        (13.8, 1.6, 'valid_until', False),
    ]
    for ax_pos, ay_pos, name, is_pk in coup_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_coupon[0], ax_pos], [c_coupon[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # REVIEW Attributes
    rev_attrs = [
        (17.2, 1.2, 'review_id', True),
        (18.5, 1.0, 'rating (1 to 5)', False),
        (19.8, 1.2, 'comment', False),
    ]
    for ax_pos, ay_pos, name, is_pk in rev_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_review[0], ax_pos], [c_review[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    # CATEGORY Attributes
    cat_attrs = [
        (22.6, 1.2, 'category_id', True),
        (24.0, 1.0, 'name', False),
        (25.4, 1.2, 'slug', False),
    ]
    for ax_pos, ay_pos, name, is_pk in cat_attrs:
        draw_attribute(ax_pos, ay_pos, name, is_pk)
        ax.plot([c_category[0], ax_pos], [c_category[1], ay_pos], color=line_color, lw=0.9, zorder=1)

    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(output_pdf, bbox_inches='tight', facecolor='white')
    plt.savefig(output_svg, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Successfully generated {output_png}, {output_pdf}, and {output_svg}")

if __name__ == '__main__':
    create_chen_erd()
