/**
 * StyleHub — Real-Time Mini Cart Drawer & Free Shipping Meter Engine
 */

async function fetchCartDrawerData() {
  try {
    const res = await fetch('/cart/api/drawer/');
    const data = await res.json();
    return data;
  } catch (err) {
    console.error('Cart drawer fetch error:', err);
    return null;
  }
}

function renderCartDrawer(data) {
  if (!data) return;

  // Counts
  const countBadge = document.getElementById('cart-drawer-count');
  const navCountDesk = document.getElementById('navbar-cart-count');
  const navCountMob = document.getElementById('navbar-cart-count-mobile');

  if (countBadge) countBadge.textContent = data.cart_count;
  if (navCountDesk) {
    navCountDesk.textContent = data.cart_count;
    navCountDesk.style.display = data.cart_count > 0 ? 'inline-flex' : 'none';
  }
  if (navCountMob) {
    navCountMob.textContent = data.cart_count;
    navCountMob.style.display = data.cart_count > 0 ? 'inline-flex' : 'none';
  }

  // Free Shipping Meter
  const meterText = document.getElementById('shipping-meter-text');
  const meterPercent = document.getElementById('shipping-meter-percent');
  const meterBar = document.getElementById('shipping-meter-bar');

  if (meterBar && meterText && meterPercent) {
    if (data.free_shipping_eligible) {
      meterText.innerHTML = '<span class="text-success fw-bold"><i class="bi bi-patch-check-fill me-1"></i> You have unlocked FREE Express Delivery!</span>';
      meterPercent.textContent = '100%';
      meterBar.style.width = '100%';
      meterBar.className = 'progress-bar bg-success';
    } else {
      meterText.innerHTML = `<i class="bi bi-truck me-1"></i> Add <strong>₹${data.amount_needed_for_free_shipping.toFixed(2)}</strong> for FREE Delivery`;
      meterPercent.textContent = `${data.free_shipping_percent}%`;
      meterBar.style.width = `${data.free_shipping_percent}%`;
      meterBar.className = 'progress-bar bg-gradient-gold';
    }
  }

  // Body and Items
  const itemsList = document.getElementById('cart-drawer-items-list');
  const emptyState = document.getElementById('cart-drawer-empty');
  const footer = document.getElementById('cart-drawer-footer');
  const upsellBox = document.getElementById('cart-drawer-upsell');

  if (!data.items || data.items.length === 0) {
    if (itemsList) itemsList.innerHTML = '';
    if (emptyState) emptyState.classList.remove('d-none');
    if (footer) footer.classList.add('d-none');
    if (upsellBox) upsellBox.classList.add('d-none');
    return;
  }

  if (emptyState) emptyState.classList.add('d-none');
  if (footer) footer.classList.remove('d-none');

  if (itemsList) {
    itemsList.innerHTML = data.items.map(item => `
      <div class="cart-drawer-item d-flex gap-3 py-3 border-bottom position-relative align-items-center" id="drawer-item-${item.id}">
        <a href="/product/${item.product_slug}/" class="flex-shrink-0">
          <img src="${item.image_url}" alt="${item.product_name}" class="rounded-3 object-fit-cover shadow-xs" style="width: 68px; height: 78px;">
        </a>
        <div class="flex-grow-1 min-w-0">
          <div class="d-flex justify-content-between align-items-start gap-1">
            <a href="/product/${item.product_slug}/" class="text-reset text-decoration-none fw-semibold small text-truncate d-block mb-1">
              ${item.product_name}
            </a>
            <button type="button" class="btn btn-sm btn-link text-muted p-0 drawer-remove-btn" data-item-id="${item.id}" title="Remove">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
          <div class="small text-muted mb-2 font-monospace" style="font-size: 0.76rem;">
            ${item.size ? `<span class="badge bg-secondary-subtle text-secondary me-1">${item.size}</span>` : ''}
            ${item.color ? `<span class="text-muted">${item.color}</span>` : ''}
          </div>
          <div class="d-flex justify-content-between align-items-center">
            <div class="input-group input-group-sm" style="width: 96px;">
              <button class="btn btn-outline-secondary btn-sm drawer-qty-btn px-2 py-0" type="button" data-item-id="${item.id}" data-action="decrease">-</button>
              <input type="text" class="form-control form-control-sm text-center px-1 py-0 bg-transparent" value="${item.quantity}" readonly style="max-width: 36px;">
              <button class="btn btn-outline-secondary btn-sm drawer-qty-btn px-2 py-0" type="button" data-item-id="${item.id}" data-action="increase">+</button>
            </div>
            <div class="fw-bold small text-end">
              ₹${item.total_price.toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    `).join('');
  }

  // Footer totals
  const subtotalEl = document.getElementById('cart-drawer-subtotal');
  const discountEl = document.getElementById('cart-drawer-discount');
  const discountRow = document.getElementById('cart-drawer-discount-row');
  const shippingEl = document.getElementById('cart-drawer-shipping');

  if (subtotalEl) subtotalEl.textContent = `₹${data.subtotal.toFixed(2)}`;
  if (discountRow) {
    if (data.discount > 0) {
      discountRow.style.setProperty('display', 'flex', 'important');
      if (discountEl) discountEl.textContent = `-₹${data.discount.toFixed(2)}`;
    } else {
      discountRow.style.setProperty('display', 'none', 'important');
    }
  }
  if (shippingEl) {
    shippingEl.textContent = data.shipping === 0 ? 'FREE' : `₹${data.shipping.toFixed(2)}`;
  }

  // Upsell
  if (data.upsell && upsellBox) {
    upsellBox.classList.remove('d-none');
    const uImg = document.getElementById('upsell-img');
    const uName = document.getElementById('upsell-name');
    const uPrice = document.getElementById('upsell-price');
    const uBtn = document.getElementById('upsell-add-btn');

    if (uImg) uImg.src = data.upsell.image_url;
    if (uName) uName.textContent = data.upsell.name;
    if (uPrice) uPrice.textContent = `₹${data.upsell.price.toFixed(2)}`;
    if (uBtn) {
      uBtn.dataset.variantId = data.upsell.variant_id;
      uBtn.disabled = false;
      uBtn.textContent = '+ Add';
    }
  } else if (upsellBox) {
    upsellBox.classList.add('d-none');
  }
}

// Global function to open Cart Drawer
window.openCartDrawer = async function() {
  const offcanvasEl = document.getElementById('cartDrawerOffcanvas');
  if (!offcanvasEl) return;
  const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
  bsOffcanvas.show();

  const data = await fetchCartDrawerData();
  renderCartDrawer(data);
};

// Global function to refresh Cart Drawer in background
window.refreshCartDrawer = async function() {
  const data = await fetchCartDrawerData();
  renderCartDrawer(data);
  return data;
};

document.addEventListener('DOMContentLoaded', () => {
  // Wire drawer triggers
  document.addEventListener('click', async (e) => {
    const trigger = e.target.closest('.cart-drawer-trigger');
    if (trigger) {
      e.preventDefault();
      await window.openCartDrawer();
      return;
    }

    // Drawer Qty Stepper
    const qtyBtn = e.target.closest('.drawer-qty-btn');
    if (qtyBtn) {
      e.preventDefault();
      const itemId = qtyBtn.dataset.itemId;
      const action = qtyBtn.dataset.action;
      const input = qtyBtn.parentElement.querySelector('input');
      const curQty = parseInt(input.value) || 1;
      const newQty = action === 'increase' ? curQty + 1 : curQty - 1;

      if (newQty < 1) return;

      const fd = new FormData();
      fd.append('item_id', itemId);
      fd.append('quantity', newQty);

      try {
        const res = await fetch('/cart/api/update/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: fd
        });
        const d = await res.json();
        if (d.success) {
          await window.refreshCartDrawer();
        } else {
          showToast(d.message || 'Could not update quantity', 'error');
        }
      } catch (err) {
        console.error('Drawer update error:', err);
      }
      return;
    }

    // Drawer Remove Button
    const removeBtn = e.target.closest('.drawer-remove-btn');
    if (removeBtn) {
      e.preventDefault();
      const itemId = removeBtn.dataset.itemId;
      const fd = new FormData();
      fd.append('item_id', itemId);

      try {
        const res = await fetch('/cart/api/remove/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: fd
        });
        const d = await res.json();
        if (d.success) {
          await window.refreshCartDrawer();
          showToast('Item removed from bag', 'info');
        }
      } catch (err) {
        console.error('Drawer remove error:', err);
      }
      return;
    }

    // Drawer Upsell Add Button
    const upsellBtn = e.target.closest('#upsell-add-btn');
    if (upsellBtn) {
      e.preventDefault();
      const variantId = upsellBtn.dataset.variantId;
      if (!variantId) return;

      upsellBtn.disabled = true;
      upsellBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

      const fd = new FormData();
      fd.append('variant_id', variantId);
      fd.append('quantity', 1);

      try {
        const res = await fetch('/cart/api/add/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: fd
        });
        const d = await res.json();
        if (d.success) {
          showToast('Added accessory to bag!', 'success');
          await window.refreshCartDrawer();
        } else {
          showToast(d.message || 'Could not add upsell', 'error');
          upsellBtn.disabled = false;
          upsellBtn.textContent = '+ Add';
        }
      } catch (err) {
        console.error('Upsell add error:', err);
        upsellBtn.disabled = false;
        upsellBtn.textContent = '+ Add';
      }
    }
  });

  // Load drawer data when offcanvas is opened
  const offcanvasEl = document.getElementById('cartDrawerOffcanvas');
  if (offcanvasEl) {
    offcanvasEl.addEventListener('show.bs.offcanvas', () => {
      fetchCartDrawerData().then(renderCartDrawer);
    });
  }
});
