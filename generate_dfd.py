import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_dfd_diagrams():
    border_color = '#111827'
    bg_color = '#FFFFFF'
    text_color = '#111827'
    line_color = '#1F2937'
    font_family = 'sans-serif'

    # Helper: Entity
    def draw_external_entity(ax, x, y, name, w=2.4, h=4.8):
        rect = patches.Rectangle((x - w/2, y - h/2), w, h,
                                 linewidth=1.6, edgecolor=border_color, facecolor=bg_color, zorder=3)
        ax.add_patch(rect)
        ax.text(x, y, name, fontsize=11, fontweight='bold', ha='center', va='center',
                family=font_family, color=text_color, zorder=4)
        return (x, y)

    # Helper: Process (Oval)
    def draw_process(ax, x, y, proc_num, name, w=2.6, h=1.35):
        ellipse = patches.Ellipse((x, y), width=w, height=h,
                                  linewidth=1.5, edgecolor=border_color, facecolor=bg_color, zorder=3)
        ax.add_patch(ellipse)
        ax.text(x, y + 0.22, proc_num, fontsize=10, fontweight='bold', ha='center', va='center',
                family=font_family, color=text_color, zorder=4)
        ax.text(x, y - 0.18, name, fontsize=9.0, ha='center', va='center',
                family=font_family, color=text_color, zorder=4)
        return (x, y)

    # Helper: Data Store
    def draw_data_store(ax, x, y, store_id, name, w=3.6, h=0.85):
        x0, y0 = x - w/2, y - h/2
        id_w = 0.75
        ax.plot([x0, x0 + w], [y0 + h, y0 + h], color=border_color, lw=1.5, zorder=3)
        ax.plot([x0, x0 + w], [y0, y0], color=border_color, lw=1.5, zorder=3)
        ax.plot([x0, x0], [y0, y0 + h], color=border_color, lw=1.5, zorder=3)
        ax.plot([x0 + id_w, x0 + id_w], [y0, y0 + h], color=border_color, lw=1.2, zorder=3)
        
        ax.text(x0 + id_w/2, y, store_id, fontsize=9.5, fontweight='bold', ha='center', va='center',
                family=font_family, color=text_color, zorder=4)
        ax.text(x0 + id_w + (w - id_w)/2, y, name, fontsize=8.5, ha='center', va='center',
                family=font_family, color=text_color, zorder=4)
        return (x, y)

    # Helper: Arrow
    def draw_arrow(ax, p1, p2, label=None, label_offset=(0, 0.14)):
        arrow_props = dict(arrowstyle='->,head_width=0.22,head_length=0.32',
                           lw=1.2, color=line_color, shrinkA=2, shrinkB=2)
        ax.annotate('', xy=p2, xytext=p1, arrowprops=arrow_props, zorder=2)
        if label:
            mid_x = (p1[0] + p2[0]) / 2 + label_offset[0]
            mid_y = (p1[1] + p2[1]) / 2 + label_offset[1]
            ax.text(mid_x, mid_y, label, fontsize=8.0, ha='center', va='center',
                    family=font_family, color='#1F2937',
                    bbox=dict(boxstyle='square,pad=0.12', facecolor='white', edgecolor='none', alpha=0.9),
                    zorder=4)

    # =========================================================================
    # 1. DFD LEVEL 1 - CUSTOMER FLOW (Matches Page 17 of PDF)
    # =========================================================================
    fig1 = plt.figure(figsize=(13, 11), dpi=300)
    ax1 = fig1.add_subplot(111)
    ax1.set_xlim(0, 13)
    ax1.set_ylim(0, 11)
    ax1.axis('off')

    # Border frame
    frame1 = patches.Rectangle((0.4, 0.4), 12.2, 10.2, linewidth=1.4, edgecolor='#333333', facecolor='none', zorder=1)
    ax1.add_patch(frame1)

    ax1.text(0.7, 10.2, 'LEVEL 1 for CUSTOMER', fontsize=11, fontweight='bold', family=font_family, color='#111827')
    ax1.text(6.5, 9.75, 'Data Flow Diagram - Customer', fontsize=13, fontweight='bold', ha='center', family=font_family, color='#111827')

    # Nodes
    draw_external_entity(ax1, 1.8, 5.0, 'Customer\n(User)', w=2.0, h=5.2)

    p1 = draw_process(ax1, 6.2, 8.4, '1.0', 'Register /\nLogin')
    p2 = draw_process(ax1, 6.2, 6.1, '2.0', 'Browse\nProducts')
    p3 = draw_process(ax1, 6.2, 3.8, '3.0', 'Manage\nCart')
    p4 = draw_process(ax1, 6.2, 1.5, '4.0', 'Place\nOrder')

    d1 = draw_data_store(ax1, 10.4, 8.4, 'D1', 'User Database\n(auth_user)')
    d2 = draw_data_store(ax1, 10.4, 6.1, 'D2', 'Product Database\n(products_product)')
    d3 = draw_data_store(ax1, 10.4, 3.8, 'D3', 'Cart Database\n(cart_cart, cartitem)')
    d4 = draw_data_store(ax1, 10.4, 1.5, 'D4', 'Order Database\n(orders_order, payment)')

    # Customer <---> 1.0 Register / Login
    draw_arrow(ax1, (2.8, 6.8), (5.0, 8.6), 'Registration / Login Details', label_offset=(-0.5, 0.18))
    draw_arrow(ax1, (5.0, 8.1), (2.8, 6.2), 'Account Confirmation', label_offset=(-0.4, -0.16))
    draw_arrow(ax1, (7.5, 8.6), (8.6, 8.6), 'Store User Data', label_offset=(0, 0.15))
    draw_arrow(ax1, (8.6, 8.2), (7.5, 8.2), 'User Data', label_offset=(0, -0.15))

    # Customer <---> 2.0 Browse Products
    draw_arrow(ax1, (2.8, 5.6), (4.9, 6.3), 'Search Products, View Catalog', label_offset=(-0.4, 0.18))
    draw_arrow(ax1, (4.9, 5.8), (2.8, 5.0), 'Product Information', label_offset=(-0.4, -0.16))
    draw_arrow(ax1, (8.6, 6.1), (7.5, 6.1), 'Get Product Details', label_offset=(0, 0.15))

    # Customer <---> 3.0 Manage Cart
    draw_arrow(ax1, (2.8, 4.4), (4.9, 4.0), 'Add to Cart / Update Quantity', label_offset=(-0.4, 0.18))
    draw_arrow(ax1, (7.5, 4.0), (8.6, 4.0), 'Store Cart Details', label_offset=(0, 0.15))
    draw_arrow(ax1, (8.6, 3.6), (7.5, 3.6), 'Cart Information', label_offset=(0, -0.15))

    # Customer <---> 4.0 Place Order
    draw_arrow(ax1, (2.8, 3.8), (5.0, 1.7), 'Place Order & Submit Payment', label_offset=(-0.5, 0.18))
    draw_arrow(ax1, (5.0, 1.3), (2.8, 3.2), 'Order Status, Invoice', label_offset=(-0.5, -0.16))
    draw_arrow(ax1, (7.5, 1.7), (8.6, 1.7), 'Store Order Details', label_offset=(0, 0.15))
    draw_arrow(ax1, (8.6, 1.3), (7.5, 1.3), 'Order Confirmation', label_offset=(0, -0.15))

    plt.tight_layout()
    plt.savefig('STYLEHUB_DFD_Level1_Customer.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig('STYLEHUB_DFD_Level1_Customer.pdf', bbox_inches='tight', facecolor='white')
    plt.savefig('STYLEHUB_DFD_Level1_Customer.svg', bbox_inches='tight', facecolor='white')
    plt.close(fig1)

    # =========================================================================
    # 2. DFD LEVEL 1 - ADMIN FLOW (Matches Page 18 of PDF, Harmonized)
    # =========================================================================
    fig2 = plt.figure(figsize=(13, 11), dpi=300)
    ax2 = fig2.add_subplot(111)
    ax2.set_xlim(0, 13)
    ax2.set_ylim(0, 11)
    ax2.axis('off')

    # Border frame
    frame2 = patches.Rectangle((0.4, 0.4), 12.2, 10.2, linewidth=1.4, edgecolor='#333333', facecolor='none', zorder=1)
    ax2.add_patch(frame2)

    ax2.text(0.7, 10.2, 'LEVEL 1 for ADMIN', fontsize=11, fontweight='bold', family=font_family, color='#111827')
    ax2.text(6.5, 9.75, 'Data Flow Diagram - Admin', fontsize=13, fontweight='bold', ha='center', family=font_family, color='#111827')

    # Nodes
    draw_external_entity(ax2, 1.8, 5.0, 'Admin\n(Staff)', w=2.0, h=5.2)

    p1_a = draw_process(ax2, 6.2, 8.4, '1.0', 'Login')
    p2_a = draw_process(ax2, 6.2, 6.1, '2.0', 'Manage\nProducts')
    p3_a = draw_process(ax2, 6.2, 3.8, '3.0', 'Manage\nOrders')
    p4_a = draw_process(ax2, 6.2, 1.5, '4.0', 'View\nReports')

    # Harmonized Data Stores (Consistent D1, D2, D4 numbering matching database tables)
    d1_a = draw_data_store(ax2, 10.4, 8.4, 'D1', 'User Database\n(auth_user: is_staff)')
    d2_a = draw_data_store(ax2, 10.4, 6.1, 'D2', 'Product Database\n(products_product)')
    d4_a = draw_data_store(ax2, 10.4, 3.8, 'D4', 'Order Database\n(orders_order)')
    d4_rep = draw_data_store(ax2, 10.4, 1.5, 'D4', 'Order & Sales Data\n(orders_order, payment)')

    # Admin <---> 1.0 Login
    draw_arrow(ax2, (2.8, 6.8), (5.0, 8.6), 'Login Credentials', label_offset=(-0.5, 0.18))
    draw_arrow(ax2, (5.0, 8.1), (2.8, 6.2), 'Access Approved / Dashboard', label_offset=(-0.4, -0.16))
    draw_arrow(ax2, (7.5, 8.6), (8.6, 8.6), 'Verify Credentials', label_offset=(0, 0.15))
    draw_arrow(ax2, (8.6, 8.2), (7.5, 8.2), 'User Privileges', label_offset=(0, -0.15))

    # Admin <---> 2.0 Manage Products
    draw_arrow(ax2, (2.8, 5.6), (4.9, 6.3), 'Add / Update / Delete Product', label_offset=(-0.4, 0.18))
    draw_arrow(ax2, (7.5, 6.3), (8.6, 6.3), 'Write Product Updates', label_offset=(0, 0.15))
    draw_arrow(ax2, (8.6, 5.9), (7.5, 5.9), 'Product Information', label_offset=(0, -0.15))

    # Admin <---> 3.0 Manage Orders
    draw_arrow(ax2, (2.8, 4.4), (4.9, 4.0), 'View / Update Order Status', label_offset=(-0.4, 0.18))
    draw_arrow(ax2, (7.5, 4.0), (8.6, 4.0), 'Update Order Records', label_offset=(0, 0.15))
    draw_arrow(ax2, (8.6, 3.6), (7.5, 3.6), 'Order Information', label_offset=(0, -0.15))

    # Admin <---> 4.0 View Reports
    draw_arrow(ax2, (2.8, 3.8), (5.0, 1.7), 'Request Sales & Order Reports', label_offset=(-0.5, 0.18))
    draw_arrow(ax2, (5.0, 1.3), (2.8, 3.2), 'Analytics & Revenue Reports', label_offset=(-0.5, -0.16))
    draw_arrow(ax2, (7.5, 1.7), (8.6, 1.7), 'Query Order Sales Data', label_offset=(0, 0.15))
    draw_arrow(ax2, (8.6, 1.3), (7.5, 1.3), 'Sales Summary Records', label_offset=(0, -0.15))

    plt.tight_layout()
    plt.savefig('STYLEHUB_DFD_Level1_Admin.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig('STYLEHUB_DFD_Level1_Admin.pdf', bbox_inches='tight', facecolor='white')
    plt.savefig('STYLEHUB_DFD_Level1_Admin.svg', bbox_inches='tight', facecolor='white')
    plt.close(fig2)

    print("Successfully generated all DFD diagrams in PNG, PDF, and SVG formats.")

if __name__ == '__main__':
    create_dfd_diagrams()
