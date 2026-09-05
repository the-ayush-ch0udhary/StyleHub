/**
 * StyleHub — Interactive Shopping Bag & Coupon Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  const cartContainer = document.getElementById('cart-page-container');
  if (!cartContainer) return;

  function updateOrderSummaryUI(data) {
    const subtotalEl = document.getElementById('cart-subtotal-val');
    const discountEl = document.getElementById('cart-discount-val');
    const shippingEl = document.getElementById('cart-shipping-val');
    const taxEl = document.getElementById('cart-tax-val');
    const totalEl = document.getElementById('cart-total-val');
    const discountRow = document.getElementById('cart-discount-row');
    const cartCountNav = document.getElementById('navbar-cart-count');

    if (subtotalEl) subtotalEl.textContent = `₹${data.subtotal.toFixed(2)}`;
    if (shippingEl) {
      shippingEl.textContent = data.shipping === 0 ? 'FREE' : `₹${data.shipping.toFixed(2)}`;
      if (data.shipping === 0) shippingEl.className = 'text-success fw-bold';
    }
    if (taxEl) taxEl.textContent = `₹${data.tax.toFixed(2)}`;
    if (totalEl) totalEl.textContent = `₹${data.total.toFixed(2)}`;

    if (discountRow) {
      if (data.discount > 0) {
        discountRow.style.display = 'flex';
        if (discountEl) discountEl.textContent = `-₹${data.discount.toFixed(2)}`;
      } else {
        discountRow.style.display = 'none';
      }
    }

    if (cartCountNav) {
      cartCountNav.textContent = data.cart_count;
      cartCountNav.style.display = data.cart_count > 0 ? 'inline-flex' : 'none';
    }
  }

  // Quantity Change Handler
  cartContainer.addEventListener('click', async (e) => {
    const btn = e.target.closest('.cart-qty-btn');
    if (!btn) return;

    const action = btn.dataset.action;
    const itemId = btn.dataset.itemId;
    const input = document.getElementById(`qty-input-${itemId}`);
    if (!input) return;

    let currentQty = parseInt(input.value) || 1;
    let newQty = action === 'increase' ? currentQty + 1 : currentQty - 1;

    if (newQty < 1) return;

    const formData = new FormData();
    formData.append('item_id', itemId);
    formData.append('quantity', newQty);

    try {
      const res = await fetch('/cart/api/update/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: formData,
      });

      const data = await res.json();
      if (data.success) {
        input.value = newQty;
        const lineTotalEl = document.getElementById(`item-total-${itemId}`);
        if (lineTotalEl) lineTotalEl.textContent = `₹${data.item_total.toFixed(2)}`;
        updateOrderSummaryUI(data);
        showToast(data.message, 'success');
      } else {
        showToast(data.message, 'error');
      }
    } catch (err) {
      console.error('Update cart error:', err);
    }
  });

  // Remove Item Handler
  cartContainer.addEventListener('click', async (e) => {
    const removeBtn = e.target.closest('.cart-remove-btn');
    if (!removeBtn) return;
    e.preventDefault();

    const itemId = removeBtn.dataset.itemId;
    const formData = new FormData();
    formData.append('item_id', itemId);

    try {
      const res = await fetch('/cart/api/remove/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: formData,
      });

      const data = await res.json();
      if (data.success) {
        const itemRow = document.getElementById(`cart-row-${itemId}`);
        if (itemRow) itemRow.remove();
        updateOrderSummaryUI(data);
        showToast(data.message, 'success');

        if (data.cart_count === 0) {
          window.location.reload();
        }
      }
    } catch (err) {
      console.error('Remove cart error:', err);
    }
  });

  // Coupon Application
  const couponForm = document.getElementById('coupon-form');
  if (couponForm) {
    couponForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const codeInput = document.getElementById('coupon-code-input');
      const code = codeInput ? codeInput.value.trim() : '';

      if (!code) {
        showToast('Please enter a coupon code.', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('coupon_code', code);

      try {
        const res = await fetch('/coupons/api/apply/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: formData,
        });

        const data = await res.json();
        if (data.success) {
          showToast(data.message, 'success');
          updateOrderSummaryUI(data);
          const badgeWrap = document.getElementById('applied-coupon-badge-wrap');
          if (badgeWrap) {
            badgeWrap.innerHTML = `
              <div class="d-flex align-items-center justify-content-between p-2 mt-2 rounded bg-success bg-opacity-10 border border-success">
                <span class="text-success fw-bold"><i class="bi bi-tag-fill me-1"></i> ${data.coupon_code}</span>
                <button type="button" id="remove-coupon-btn" class="btn btn-sm btn-link text-danger p-0">Remove</button>
              </div>
            `;
            attachRemoveCouponHandler();
          }
        } else {
          showToast(data.message, 'error');
        }
      } catch (err) {
        console.error('Apply coupon error:', err);
      }
    });
  }

  function attachRemoveCouponHandler() {
    const removeBtn = document.getElementById('remove-coupon-btn');
    if (!removeBtn) return;

    removeBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/coupons/api/remove/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        const data = await res.json();
        if (data.success) {
          showToast(data.message, 'info');
          updateOrderSummaryUI(data);
          const badgeWrap = document.getElementById('applied-coupon-badge-wrap');
          if (badgeWrap) badgeWrap.innerHTML = '';
          const codeInput = document.getElementById('coupon-code-input');
          if (codeInput) codeInput.value = '';
        }
      } catch (err) {
        console.error('Remove coupon error:', err);
      }
    });
  }

  attachRemoveCouponHandler();
});
