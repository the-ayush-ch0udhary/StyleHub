/**
 * StyleHub — Checkout & Payment Engine
 * Razorpay Test/Live + COD
 */

document.addEventListener('DOMContentLoaded', () => {
  const checkoutBtn = document.getElementById('place-order-btn');

  if (!checkoutBtn) return;

  checkoutBtn.addEventListener('click', async (e) => {
    e.preventDefault();

    // --------------------------------------------------
    // 1. Get selected address
    // --------------------------------------------------
    const selectedAddressInput =
      document.querySelector('input[name="selected_address"]:checked');

    if (!selectedAddressInput) {
      showToast('Please select a shipping address.', 'error');
      return;
    }

    const addressId = selectedAddressInput.value;

    // --------------------------------------------------
    // 2. Get payment method
    // --------------------------------------------------
    const paymentMethodInput =
      document.querySelector('input[name="payment_method"]:checked');

    const paymentMethod = paymentMethodInput
      ? paymentMethodInput.value
      : 'RAZORPAY';

    // --------------------------------------------------
    // 3. Disable checkout button
    // --------------------------------------------------
    checkoutBtn.disabled = true;

    const originalText = checkoutBtn.innerHTML;

    checkoutBtn.innerHTML = `
      <span
        class="spinner-border spinner-border-sm me-2"
        role="status"
        aria-hidden="true"
      ></span>
      Processing Secure Order...
    `;

    // ==================================================
    // COD
    // ==================================================
    if (paymentMethod === 'COD') {
      const formData = new FormData();

      formData.append('address_id', addressId);

      try {
        const res = await fetch('/payments/cod-place-order/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: formData,
        });

        const data = await res.json();

        if (data.success && data.redirect_url) {
          window.location.href = data.redirect_url;
          return;
        }

        showToast(
          data.message || 'Could not place COD order.',
          'error'
        );

        checkoutBtn.disabled = false;
        checkoutBtn.innerHTML = originalText;

      } catch (err) {
        console.error('COD error:', err);

        showToast(
          'An error occurred while placing your order.',
          'error'
        );

        checkoutBtn.disabled = false;
        checkoutBtn.innerHTML = originalText;
      }

      return;
    }

    // ==================================================
    // RAZORPAY
    // ==================================================

    const formData = new FormData();

    formData.append('address_id', addressId);

    try {
      // ------------------------------------------------
      // Create Razorpay order
      // ------------------------------------------------
      const res = await fetch(
        '/payments/create-razorpay-order/',
        {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: formData,
        }
      );

      const data = await res.json();

      console.log(
        'Razorpay order response:',
        data
      );

      if (!data.success) {
        showToast(
          data.message ||
          'Error initiating payment gateway.',
          'error'
        );

        checkoutBtn.disabled = false;
        checkoutBtn.innerHTML = originalText;

        return;
      }

      // ------------------------------------------------
      // Check Razorpay SDK
      // ------------------------------------------------
      if (typeof Razorpay === 'undefined') {
        console.error(
          'Razorpay SDK is not loaded.'
        );

        showToast(
          'Payment gateway could not be loaded. Please refresh and try again.',
          'error'
        );

        checkoutBtn.disabled = false;
        checkoutBtn.innerHTML = originalText;

        return;
      }

      // ------------------------------------------------
      // Razorpay Checkout options
      // ------------------------------------------------
      const options = {

        key: data.key_id,

        amount: data.amount,

        currency: data.currency,

        name: 'StyleHub Luxury Fashion',

        description:
          `Order #${data.order_number}`,

        order_id:
          data.razorpay_order_id,

        image:
          '/static/images/logo.png',

        prefill: {
          name:
            data.customer_name || '',

          email:
            data.customer_email || '',

          contact:
            data.customer_phone || '',
        },

        theme: {
          color: '#111827',
        },

        // ------------------------------------------------
        // SUCCESS
        // ------------------------------------------------
        handler: async function (response) {

          console.log(
            'RAZORPAY PAYMENT SUCCESS RESPONSE:',
            response
          );

          try {

            const verifyRes =
              await fetch(
                '/payments/verify/',
                {
                  method: 'POST',

                  headers: {
                    'Content-Type':
                      'application/json',

                    'X-CSRFToken':
                      csrftoken,

                    'X-Requested-With':
                      'XMLHttpRequest',
                  },

                  body: JSON.stringify({

                    order_number:
                      data.order_number,

                    razorpay_order_id:
                      response.razorpay_order_id,

                    razorpay_payment_id:
                      response.razorpay_payment_id,

                    razorpay_signature:
                      response.razorpay_signature,

                  }),
                }
              );

            const verifyData =
              await verifyRes.json();

            console.log(
              'PAYMENT VERIFICATION RESPONSE:',
              verifyData
            );

            if (
              verifyData.success &&
              verifyData.redirect_url
            ) {

              window.location.href =
                verifyData.redirect_url;

              return;
            }

            console.error(
              'Payment verification failed:',
              verifyData
            );

            showToast(
              verifyData.message ||
              'Payment verification failed.',
              'error'
            );

            window.location.href =
              `/payments/failed/?order_number=${encodeURIComponent(
                data.order_number
              )}`;

          } catch (verifyError) {

            console.error(
              'Payment verification error:',
              verifyError
            );

            window.location.href =
              `/payments/failed/?order_number=${encodeURIComponent(
                data.order_number
              )}`;
          }
        },

        // ------------------------------------------------
        // MODAL DISMISSED
        // ------------------------------------------------
        modal: {

          ondismiss: function () {

            console.log(
              'Razorpay checkout dismissed.'
            );

            checkoutBtn.disabled = false;

            checkoutBtn.innerHTML =
              originalText;

            showToast(
              'Payment was cancelled. Your bag items are preserved.',
              'info'
            );
          },

        },

        retry: {
          enabled: true,
          max_count: 4,
        },
      };

      // ------------------------------------------------
      // Create Razorpay instance
      // ------------------------------------------------
      const rzp =
        new Razorpay(options);

      // ------------------------------------------------
      // PAYMENT FAILED
      // ------------------------------------------------
      rzp.on(
        'payment.failed',
        function (response) {

          console.error(
            '===================================='
          );

          console.error(
            'RAZORPAY PAYMENT FAILED'
          );

          console.error(
            'Full response:',
            response
          );

          console.error(
            'Error object:',
            response.error
          );

          console.error(
            'Code:',
            response.error?.code
          );

          console.error(
            'Description:',
            response.error?.description
          );

          console.error(
            'Source:',
            response.error?.source
          );

          console.error(
            'Step:',
            response.error?.step
          );

          console.error(
            'Reason:',
            response.error?.reason
          );

          console.error(
            'Metadata:',
            response.error?.metadata
          );

          console.error(
            '===================================='
          );

          // Log details for debugging
          console.warn('Razorpay payment failed:', {
            code: errorCode,
            description: description,
            source: source,
            step: step,
            reason: reason,
          });

          // Show non-blocking toast instead of disruptive alert
          showToast(description || 'Payment could not be completed. Please choose another method.', 'warning');

          // Keep checkout button enabled so user can re-try if modal closed
          checkoutBtn.disabled = false;
          checkoutBtn.innerHTML = originalText;
        }
      );

      // ------------------------------------------------
      // OPEN RAZORPAY
      // ------------------------------------------------
      console.log(
        'Opening Razorpay Checkout...'
      );

      rzp.open();

    } catch (err) {

      console.error(
        'Checkout error:',
        err
      );

      showToast(
        'Payment service unavailable. Please try again or use Cash on Delivery.',
        'error'
      );

      checkoutBtn.disabled = false;

      checkoutBtn.innerHTML =
        originalText;
    }
  });
});