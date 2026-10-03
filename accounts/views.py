import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import UserProfile, Address, EmailVerificationOTP
from .forms import UserRegistrationForm, UserLoginForm, OTPVerificationForm, UserProfileUpdateForm, AddressForm

logger = logging.getLogger(__name__)

def send_otp_email(email, otp_code, first_name=''):
    subject = f"{otp_code} is your StyleHub verification code"
    context = {
        'otp_code': otp_code,
        'first_name': first_name,
        'email': email,
    }
    html_message = render_to_string('emails/otp_verification_email.html', context)
    plain_message = (
        f"Hello {first_name or 'there'},\n\n"
        f"Your StyleHub email verification code is: {otp_code}\n\n"
        f"This code will expire in 10 minutes.\n\n"
        f"Happy Shopping,\nStyleHub Team"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'StyleHub <no-reply@stylehub.com>'
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Error sending OTP verification email to {email}: {e}")
        return False

def register_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            phone_number = form.cleaned_data.get('phone_number', '')

            from django.contrib.auth.hashers import make_password

            # Save in session for pending verification with securely hashed password
            request.session['pending_registration'] = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password_hash': make_password(password),
                'phone_number': phone_number,
            }
            request.session['otp_last_sent_at'] = int(timezone.now().timestamp())

            # Generate OTP & Send Verification Email
            otp_obj = EmailVerificationOTP.generate_otp(email=email, validity_minutes=10)
            email_sent = send_otp_email(email, otp_obj.otp_code, first_name=first_name)

            if email_sent:
                messages.info(request, f"A 6-digit verification code has been sent to {email}. Please enter it below to activate your account.")
            else:
                messages.info(request, f"Verification code generated. (Dev code: {otp_obj.otp_code}). Please enter it below.")

            return redirect('accounts:verify_otp')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')

    pending_data = request.session.get('pending_registration')
    if not pending_data:
        messages.info(request, "No pending registration found. Please complete the sign-up form.")
        return redirect('accounts:register')

    email = pending_data.get('email')
    first_name = pending_data.get('first_name', '')

    last_sent = request.session.get('otp_last_sent_at', 0)
    now_ts = int(timezone.now().timestamp())
    cooldown_remaining = max(0, 60 - (now_ts - last_sent))

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp_code']
            otp_record = EmailVerificationOTP.objects.filter(
                email__iexact=email,
                is_used=False
            ).order_by('-created_at').first()

            if not otp_record:
                messages.error(request, "No active verification code found. Please click 'Resend Code'.")
            else:
                is_valid, err_msg = otp_record.is_valid(entered_otp)
                if is_valid:
                    otp_record.mark_used()

                    # Check uniqueness before saving
                    username = pending_data['username']
                    if User.objects.filter(username__iexact=username).exists():
                        messages.error(request, "An account with this username already exists. Please register again.")
                        return redirect('accounts:register')
                    if User.objects.filter(email__iexact=email).exists():
                        messages.error(request, "An account with this email already exists.")
                        return redirect('accounts:register')

                    # Create verified user
                    user = User(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=pending_data.get('last_name', ''),
                    )
                    if 'password_hash' in pending_data:
                        user.password = pending_data['password_hash']
                    elif 'password' in pending_data:
                        user.set_password(pending_data['password'])
                    user.save()

                    # Update UserProfile
                    profile = user.profile
                    profile.phone_number = pending_data.get('phone_number', '')
                    profile.is_email_verified = True
                    profile.save()

                    # Send welcome email
                    try:
                        subject = "Welcome to StyleHub — Your Account is Verified!"
                        message = (
                            f"Hello {user.first_name or user.username},\n\n"
                            f"Thank you for verifying your email! Your StyleHub account is active and ready.\n"
                            f"Discover the latest designer apparel and exclusive collections crafted for you.\n\n"
                            f"Happy Shopping,\nThe StyleHub Team"
                        )
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
                    except Exception:
                        pass

                    # Clean up pending session
                    session_key = request.session.session_key
                    request.session.pop('pending_registration', None)
                    request.session.pop('otp_last_sent_at', None)

                    # Merge guest cart and log in
                    login(request, user)
                    from cart.services import CartService
                    if session_key:
                        CartService.merge_guest_cart(session_key, user)

                    messages.success(request, f"Email verified successfully! Welcome to StyleHub, {user.first_name or user.username}!")
                    return redirect('products:home')
                else:
                    messages.error(request, err_msg)
    else:
        form = OTPVerificationForm()

    # Mask email for display (e.g., a***h@domain.com)
    masked_email = email
    if '@' in email:
        local, domain = email.split('@', 1)
        if len(local) > 2:
            masked_email = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"
        else:
            masked_email = f"{local[0]}*@{domain}"

    context = {
        'form': form,
        'email': email,
        'masked_email': masked_email,
        'first_name': first_name,
        'cooldown_remaining': cooldown_remaining,
    }
    return render(request, 'accounts/verify_otp.html', context)

def resend_otp_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')

    pending_data = request.session.get('pending_registration')
    if not pending_data:
        messages.info(request, "No pending registration found. Please sign up below.")
        return redirect('accounts:register')

    email = pending_data.get('email')
    first_name = pending_data.get('first_name', '')
    last_sent = request.session.get('otp_last_sent_at', 0)
    now_ts = int(timezone.now().timestamp())

    if now_ts - last_sent < 60:
        remaining = 60 - (now_ts - last_sent)
        messages.warning(request, f"Please wait {remaining} seconds before requesting a new verification code.")
        return redirect('accounts:verify_otp')

    otp_obj = EmailVerificationOTP.generate_otp(email=email, validity_minutes=10)
    request.session['otp_last_sent_at'] = now_ts

    email_sent = send_otp_email(email, otp_obj.otp_code, first_name=first_name)
    if email_sent:
        messages.success(request, f"A new 6-digit verification code has been sent to {email}.")
    else:
        messages.info(request, f"New verification code generated. (Dev code: {otp_obj.otp_code}).")

    return redirect('accounts:verify_otp')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')

    next_url = request.GET.get('next') or request.POST.get('next') or 'products:home'

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            session_key = request.session.session_key
            login(request, user)

            # Merge guest cart to user cart
            from cart.services import CartService
            if session_key:
                CartService.merge_guest_cart(session_key, user)

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out securely. See you soon!")
    return redirect('products:home')

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user, profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('accounts:profile')
    else:
        form = UserProfileUpdateForm(instance=request.user, profile=profile)

    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was changed successfully!")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def address_list_view(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'accounts/addresses.html', {'addresses': addresses})

@login_required
def address_add_view(request):
    next_url = request.GET.get('next') or 'accounts:addresses'
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address added successfully!")
            return redirect(next_url)
    else:
        form = AddressForm()

    return render(request, 'accounts/address_form.html', {'form': form, 'title': 'Add New Address', 'next': next_url})

@login_required
def address_edit_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    next_url = request.GET.get('next') or 'accounts:addresses'
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully!")
            return redirect(next_url)
    else:
        form = AddressForm(instance=address)

    return render(request, 'accounts/address_form.html', {'form': form, 'title': 'Edit Address', 'next': next_url})

@login_required
def address_delete_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted successfully.")
    return redirect('accounts:addresses')

@login_required
def set_default_address_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, f"Default address set to {address.full_name}.")
    return redirect('accounts:addresses')
