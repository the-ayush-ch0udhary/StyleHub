/**
 * StyleHub Atelier AI Stylist Engine
 * Connects frontend offcanvas chat with backend /api/ai-stylist/ endpoint.
 */

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('ai-stylist-form');
  const input = document.getElementById('ai-stylist-input');
  const messagesList = document.getElementById('ai-messages-list');
  const chatBody = document.getElementById('ai-chat-body');
  const typingIndicator = document.getElementById('ai-typing-indicator');
  const engineBadge = document.getElementById('ai-engine-badge');
  const offcanvasEl = document.getElementById('aiStylistOffcanvas');

  if (!form || !input || !messagesList) return;

  let conversationHistory = [];

  // Detect current product ID if on product detail page
  let currentProductId = null;
  const productDetailWrap = document.querySelector('[data-product-id]');
  if (productDetailWrap) {
    currentProductId = productDetailWrap.getAttribute('data-product-id');
  }

  // Quick Prompt Chips
  document.querySelectorAll('.ai-chip').forEach(btn => {
    btn.addEventListener('click', function () {
      const prompt = this.getAttribute('data-prompt');
      if (prompt) {
        input.value = prompt;
        sendMessage(prompt);
      }
    });
  });

  // External trigger buttons (e.g., from product detail page)
  document.querySelectorAll('.trigger-ai-stylist').forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const customPrompt = this.getAttribute('data-ai-prompt');
      if (offcanvasEl) {
        const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        bsOffcanvas.show();
        if (customPrompt) {
          setTimeout(() => {
            input.value = customPrompt;
            sendMessage(customPrompt);
          }, 350);
        }
      }
    });
  });

  // Form submit
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    sendMessage(text);
  });

  function sendMessage(text) {
    input.value = '';
    appendUserMessage(text);
    showTyping(true);
    scrollToBottom();

    // Call API
    fetch('/api/ai-stylist/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({
        message: text,
        product_id: currentProductId,
        history: conversationHistory.slice(-4),
      })
    })
    .then(res => res.json())
    .then(data => {
      showTyping(false);
      if (data.success) {
        appendAIMessage(data.response, data.products || [], data.engine);
        conversationHistory.push({ role: 'user', text: text });
        conversationHistory.push({ role: 'model', text: data.response });
        if (data.engine && engineBadge) {
          engineBadge.textContent = `Engine: ${data.engine}`;
        }
      } else {
        appendAIMessage("I apologize, but our atelier connection encountered a brief delay. Please try asking again.", []);
      }
      scrollToBottom();
    })
    .catch(err => {
      console.error('AI Stylist error:', err);
      showTyping(false);
      appendAIMessage("Atelier concierge is momentary offline. Please check back shortly.", []);
      scrollToBottom();
    });
  }

  function appendUserMessage(text) {
    const wrap = document.createElement('div');
    wrap.className = 'd-flex gap-2 justify-content-end align-items-start user-msg-wrap mt-2';
    wrap.innerHTML = `
      <div class="p-3 rounded-4 shadow-sm" style="max-width: 85%; background: #111827; color: #ffffff; border: 1px solid rgba(217, 119, 6, 0.35); border-bottom-right-radius: 4px;">
        <p class="small mb-0" style="line-height: 1.5; color: #ffffff !important;">${escapeHtml(text)}</p>
      </div>
    `;
    messagesList.appendChild(wrap);
  }

  function appendAIMessage(markdownText, products, engine) {
    const wrap = document.createElement('div');
    wrap.className = 'd-flex gap-2 align-items-start ai-msg-wrap mt-3';

    let formattedText = renderMarkdown(markdownText);

    // Build product cards HTML if products exist
    let productsHtml = '';
    if (products && products.length > 0) {
      productsHtml = `
        <div class="mt-3 pt-2 border-top border-secondary border-opacity-25">
          <div class="small fw-bold text-uppercase tracking-wider text-muted mb-2" style="font-size: 0.72rem;">
            <i class="bi bi-bag-check me-1" style="color: var(--gold-accent, #d97706);"></i> Recommended Pieces from Atelier
          </div>
          <div class="d-flex flex-column gap-2">
            ${products.map(p => `
              <div class="card border rounded-3 p-2 shadow-sm d-flex flex-row align-items-center gap-2" style="background: var(--bg-surface, #ffffff);">
                <a href="/product/${p.slug}/" class="flex-shrink-0">
                  <img src="${p.image_url || 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=200'}" alt="${escapeHtml(p.name)}" class="rounded object-fit-cover" style="width: 52px; height: 52px;">
                </a>
                <div class="flex-grow-1 min-w-0" style="font-size: 0.8rem;">
                  <a href="/product/${p.slug}/" class="fw-bold text-body text-truncate d-block text-decoration-none" title="${escapeHtml(p.name)}">
                    ${escapeHtml(p.name)}
                  </a>
                  <div class="d-flex align-items-center gap-2 mt-0.5">
                    <span class="fw-bold text-body">₹${Math.round(p.price).toLocaleString()}</span>
                    ${p.discount_pct > 0 ? `<span class="text-muted text-decoration-line-through small" style="font-size: 0.7rem;">₹${Math.round(p.original_price).toLocaleString()}</span>` : ''}
                    <span class="badge bg-secondary rounded-pill px-1.5" style="font-size: 0.65rem;">${escapeHtml(p.category)}</span>
                  </div>
                </div>
                ${p.default_variant_id ? `
                  <button type="button" class="btn btn-sm btn-sh-gold px-2 py-1 flex-shrink-0 ai-add-bag-btn" data-variant-id="${p.default_variant_id}" title="1-Click Add to Bag" style="font-size: 0.75rem;">
                    <i class="bi bi-plus-lg"></i> Bag
                  </button>
                ` : `
                  <a href="/product/${p.slug}/" class="btn btn-sm btn-outline-dark px-2 py-1 flex-shrink-0" style="font-size: 0.75rem;">
                    View
                  </a>
                `}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    wrap.innerHTML = `
      <div class="rounded-circle flex-shrink-0 d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; background: #111827; color: #fbbf24;">
        <i class="bi bi-stars" style="font-size: 0.85rem;"></i>
      </div>
      <div class="p-3 rounded-4 shadow-sm" style="max-width: 85%; background: var(--bg-surface-alt, #f8f9fa); border: 1px solid var(--border-subtle, #e5e7eb); border-top-left-radius: 4px;">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="fw-bold small text-body">Aria • Stylist</span>
          <span class="badge bg-secondary bg-opacity-25 text-secondary font-monospace" style="font-size: 0.6rem;">${escapeHtml(engine || 'AI')}</span>
        </div>
        <div class="small text-secondary mb-0 ai-formatted-text" style="line-height: 1.6;">
          ${formattedText}
        </div>
        ${productsHtml}
      </div>
    `;

    messagesList.appendChild(wrap);

    // Bind 1-click Add to Bag inside AI response
    wrap.querySelectorAll('.ai-add-bag-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const vId = this.getAttribute('data-variant-id');
        if (vId) {
          this.disabled = true;
          this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
          fetch('/cart/api/add/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCsrfToken(),
            },
            body: `variant_id=${vId}&quantity=1`
          })
          .then(res => res.json())
          .then(data => {
            this.innerHTML = '<i class="bi bi-check-lg"></i> Added';
            this.classList.replace('btn-sh-gold', 'btn-success');
            // Update cart badges
            const mobBadge = document.getElementById('navbar-cart-count-mobile');
            const deskBadge = document.getElementById('navbar-cart-count');
            if (mobBadge) { mobBadge.textContent = data.item_count; mobBadge.style.display = 'inline-flex'; }
            if (deskBadge) { deskBadge.textContent = data.item_count; deskBadge.style.display = 'inline-flex'; }
          })
          .catch(() => {
            this.disabled = false;
            this.innerHTML = '<i class="bi bi-plus-lg"></i> Bag';
          });
        }
      });
    });
  }

  function showTyping(show) {
    if (typingIndicator) {
      if (show) {
        typingIndicator.classList.remove('d-none');
      } else {
        typingIndicator.classList.add('d-none');
      }
    }
  }

  function scrollToBottom() {
    setTimeout(() => {
      chatBody.scrollTop = chatBody.scrollHeight;
    }, 50);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function renderMarkdown(md) {
    if (!md) return '';
    let html = escapeHtml(md);
    // Headings
    html = html.replace(/### (.*?)(?:\n|$)/g, '<h6 class="fw-bold text-body mt-2 mb-1">$1</h6>');
    html = html.replace(/## (.*?)(?:\n|$)/g, '<h6 class="fw-bold text-body mt-2 mb-1">$1</h6>');
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="text-body">$1</strong>');
    // Bullet points
    html = html.replace(/(?:^|\n)- (.*?)(?=\n|$)/g, '<div class="d-flex align-items-start gap-1 my-0.5"><span class="text-warning">•</span><span>$1</span></div>');
    // Numbered lists
    html = html.replace(/(?:^|\n)(\d+)\. (.*?)(?=\n|$)/g, '<div class="d-flex align-items-start gap-1.5 my-0.5"><span class="fw-bold text-body">$1.</span><span>$2</span></div>');
    // Paragraph breaks
    html = html.replace(/\n\n/g, '<div class="my-2"></div>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }
});

