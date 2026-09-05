/**
 * StyleHub — Interactive Product Detail Page Engine
 * Handles Color Swatches, Size Selection, Dynamic Stock Status, Live Price, and AJAX Add to Bag.
 */

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('product-detail-container');
  if (!container) return;

  const productId = container.dataset.productId;
  let selectedColor = container.dataset.selectedColor || '';
  let selectedSize = container.dataset.selectedSize || '';

  const skuDisplay = document.getElementById('variant-sku');
  const priceDisplay = document.getElementById('variant-price');
  const stockBadge = document.getElementById('variant-stock-badge');
  const variantInput = document.getElementById('selected-variant-id');
  const addToBagBtn = document.getElementById('add-to-bag-btn');
  const buyNowBtn = document.getElementById('buy-now-btn');
  const qtyInput = document.getElementById('product-qty-input');

  // Thumbnail Gallery Clicker
  const mainImage = document.getElementById('main-gallery-image');
  const thumbs = document.querySelectorAll('.gallery-thumb-item');

  thumbs.forEach(thumb => {
    thumb.addEventListener('click', () => {
      thumbs.forEach(t => t.classList.remove('border-dark', 'border-2'));
      thumb.classList.add('border-dark', 'border-2');
      const targetSrc = thumb.dataset.fullSrc;
      if (mainImage && targetSrc) {
        mainImage.src = targetSrc;
      }
    });
  });

  // Quantity Stepper
  const qtyMinus = document.getElementById('qty-minus');
  const qtyPlus = document.getElementById('qty-plus');

  if (qtyMinus && qtyPlus && qtyInput) {
    qtyMinus.addEventListener('click', () => {
      let val = parseInt(qtyInput.value) || 1;
      if (val > 1) {
        qtyInput.value = val - 1;
      }
    });

    qtyPlus.addEventListener('click', () => {
      let val = parseInt(qtyInput.value) || 1;
      let maxVal = parseInt(qtyInput.max) || 99;
      if (val < maxVal) {
        qtyInput.value = val + 1;
      } else {
        showToast(`Maximum available stock reached (${maxVal})`, 'info');
      }
    });
  }

  // Check Variant Availability
  async function checkVariant() {
    if (!selectedColor || !selectedSize) {
      if (addToBagBtn) addToBagBtn.disabled = true;
      if (buyNowBtn) buyNowBtn.disabled = true;
      if (stockBadge) stockBadge.innerHTML = '<span class="text-muted"><i class="bi bi-info-circle"></i> Please select size & color</span>';
      return;
    }

    try {
      const url = `/api/variant-stock/?product_id=${productId}&color=${encodeURIComponent(selectedColor)}&size=${encodeURIComponent(selectedSize)}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.success && data.variant_id) {
        if (variantInput) variantInput.value = data.variant_id;
        if (skuDisplay) skuDisplay.textContent = data.sku;
        if (priceDisplay) priceDisplay.textContent = `₹${data.price.toFixed(2)}`;

        if (data.in_stock) {
          if (qtyInput) qtyInput.max = data.stock_quantity;
          if (addToBagBtn) addToBagBtn.disabled = false;
          if (buyNowBtn) buyNowBtn.disabled = false;

          if (data.stock_quantity <= 3) {
            stockBadge.innerHTML = `<span class="badge bg-warning text-dark"><i class="bi bi-lightning-fill"></i> Only ${data.stock_quantity} left in stock!</span>`;
          } else {
            stockBadge.innerHTML = `<span class="badge bg-success"><i class="bi bi-check-circle-fill"></i> In Stock (${data.stock_quantity} available)</span>`;
          }
        } else {
          if (addToBagBtn) addToBagBtn.disabled = true;
          if (buyNowBtn) buyNowBtn.disabled = true;
          stockBadge.innerHTML = `<span class="badge bg-danger"><i class="bi bi-x-circle-fill"></i> Out of Stock</span>`;
        }
      } else {
        if (variantInput) variantInput.value = '';
        if (addToBagBtn) addToBagBtn.disabled = true;
        if (buyNowBtn) buyNowBtn.disabled = true;
        stockBadge.innerHTML = `<span class="badge bg-secondary"><i class="bi bi-dash-circle"></i> Combination Unavailable</span>`;
      }
    } catch (err) {
      console.error('Error fetching variant stock:', err);
    }
  }

  // Color Swatch Selection
  const colorSwatches = document.querySelectorAll('.color-swatch-item');
  colorSwatches.forEach(swatch => {
    swatch.addEventListener('click', () => {
      colorSwatches.forEach(s => s.classList.remove('selected'));
      swatch.classList.add('selected');
      selectedColor = swatch.dataset.colorName;
      const colorLabel = document.getElementById('selected-color-name');
      if (colorLabel) colorLabel.textContent = selectedColor;
      checkVariant();
    });
  });

  // Size Pill Selection
  const sizePills = document.querySelectorAll('.size-pill-item');
  sizePills.forEach(pill => {
    pill.addEventListener('click', () => {
      if (pill.classList.contains('disabled')) return;
      sizePills.forEach(p => p.classList.remove('selected'));
      pill.classList.add('selected');
      selectedSize = pill.dataset.sizeVal;
      const sizeLabel = document.getElementById('selected-size-name');
      if (sizeLabel) sizeLabel.textContent = selectedSize;
      checkVariant();
    });
  });

  // Auto select initial if available
  const initialSwatch = document.querySelector('.color-swatch-item.selected') || colorSwatches[0];
  if (initialSwatch) {
    initialSwatch.click();
  }
  const initialSize = document.querySelector('.size-pill-item.selected') || sizePills[0];
  if (initialSize && !initialSize.classList.contains('disabled')) {
    initialSize.click();
  }

  // AJAX Add to Bag Form
  const addForm = document.getElementById('add-to-bag-form');
  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const variantId = variantInput.value;
      const quantity = qtyInput ? qtyInput.value : 1;

      if (!variantId) {
        showToast('Please select your preferred color and size.', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('variant_id', variantId);
      formData.append('quantity', quantity);

      try {
        const res = await fetch('/cart/api/add/', {
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
          const cartBadge = document.getElementById('navbar-cart-count');
          if (cartBadge) {
            cartBadge.textContent = data.cart_count;
            cartBadge.style.display = data.cart_count > 0 ? 'inline-flex' : 'none';
          }
        } else {
          showToast(data.message, 'error');
        }
      } catch (err) {
        console.error('Add to bag error:', err);
        showToast('Could not add to bag. Please try again.', 'error');
      }
    });
  }
});
