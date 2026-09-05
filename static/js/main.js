/**
 * StyleHub — Main JavaScript Engine
 */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Toast Notification Engine
function showToast(message, type = 'success') {
  let toastContainer = document.getElementById('sh-toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'sh-toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1090';
    document.body.appendChild(toastContainer);
  }

  const toastId = 'toast_' + Date.now();
  const icon = type === 'success' ? 'bi-check-circle-fill text-success' : (type === 'error' || type === 'danger' ? 'bi-exclamation-triangle-fill text-danger' : 'bi-info-circle-fill text-primary');
  
  const toastHtml = `
    <div id="${toastId}" class="toast align-items-center border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${icon} fs-5"></i>
          <div>${message}</div>
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);
  const toastEl = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// Global Wishlist Toggle via AJAX
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.wishlist-toggle-btn');
    if (!btn) return;
    e.preventDefault();

    const productId = btn.dataset.productId;
    if (!productId) return;

    try {
      const response = await fetch(`/wishlist/toggle/${productId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      if (response.redirected) {
        window.location.href = response.url;
        return;
      }

      const data = await response.json();
      if (data.success) {
        btn.classList.toggle('active', data.added);
        const icon = btn.querySelector('i');
        if (icon) {
          icon.className = data.added ? 'bi bi-heart-fill' : 'bi bi-heart';
        }
        
        // Update wishlist count badge in navbar
        const badge = document.getElementById('navbar-wishlist-count');
        if (badge) {
          badge.textContent = data.wishlist_count;
          badge.style.display = data.wishlist_count > 0 ? 'inline-flex' : 'none';
        }
        showToast(data.message, 'success');
      } else {
        showToast(data.message || 'Could not update wishlist', 'error');
      }
    } catch (err) {
      console.error('Wishlist error:', err);
      showToast('Please log in to manage your wishlist.', 'info');
    }
  });
});
