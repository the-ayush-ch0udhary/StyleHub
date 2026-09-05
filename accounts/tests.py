from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from accounts.models import Address, UserProfile, EmailVerificationOTP

class AccountTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )

    def test_user_profile_creation(self):
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(str(self.user.profile), "testuser's Profile")
        self.assertFalse(self.user.profile.is_email_verified)

    def test_registration_generates_otp_and_redirects_to_verify(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'phone_number': '1234567890',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        # Should redirect to verify_otp
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:verify_otp'))
        
        # User not yet in DB until OTP verified
        self.assertFalse(User.objects.filter(username='newuser').exists())
        
        # OTP generated in DB
        otp = EmailVerificationOTP.objects.filter(email='new@example.com', is_used=False).first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertTrue(otp.otp_code.isdigit())

    def test_verify_valid_otp_creates_user_and_logs_in(self):
        # 1. Start signup
        self.client.post(reverse('accounts:register'), {
            'username': 'verifieduser',
            'first_name': 'Verified',
            'last_name': 'Customer',
            'email': 'verified@example.com',
            'phone_number': '9876543210',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        otp = EmailVerificationOTP.objects.get(email='verified@example.com', is_used=False)

        # 2. Post correct OTP
        verify_resp = self.client.post(reverse('accounts:verify_otp'), {
            'otp_code': otp.otp_code
        })
        self.assertEqual(verify_resp.status_code, 302)
        self.assertEqual(verify_resp.url, reverse('products:home'))

        # 3. User created and verified
        created_user = User.objects.get(username='verifieduser')
        self.assertEqual(created_user.email, 'verified@example.com')
        self.assertTrue(created_user.profile.is_email_verified)
        self.assertEqual(created_user.profile.phone_number, '9876543210')

        # 4. OTP marked as used
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_verify_invalid_otp_rejects(self):
        self.client.post(reverse('accounts:register'), {
            'username': 'wrongotpuser',
            'first_name': 'Wrong',
            'last_name': 'OTP',
            'email': 'wrong@example.com',
            'phone_number': '9876543210',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        
        # Post wrong OTP
        verify_resp = self.client.post(reverse('accounts:verify_otp'), {
            'otp_code': '000000'
        })
        self.assertEqual(verify_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='wrongotpuser').exists())

    def test_expired_otp_rejects(self):
        self.client.post(reverse('accounts:register'), {
            'username': 'expireduser',
            'first_name': 'Expired',
            'last_name': 'User',
            'email': 'expired@example.com',
            'phone_number': '9876543210',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        otp = EmailVerificationOTP.objects.get(email='expired@example.com', is_used=False)
        # Manually expire
        otp.expires_at = timezone.now() - timedelta(minutes=5)
        otp.save()

        verify_resp = self.client.post(reverse('accounts:verify_otp'), {
            'otp_code': otp.otp_code
        })
        self.assertEqual(verify_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='expireduser').exists())

    def test_resend_otp_generates_new_code(self):
        self.client.post(reverse('accounts:register'), {
            'username': 'resenduser',
            'first_name': 'Resend',
            'last_name': 'User',
            'email': 'resend@example.com',
            'phone_number': '9876543210',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        initial_otp = EmailVerificationOTP.objects.get(email='resend@example.com', is_used=False)

        # Set session timestamp back so cooldown passes
        session = self.client.session
        session['otp_last_sent_at'] = int((timezone.now() - timedelta(seconds=70)).timestamp())
        session.save()

        resend_resp = self.client.post(reverse('accounts:resend_otp'))
        self.assertEqual(resend_resp.status_code, 302)

        initial_otp.refresh_from_db()
        self.assertTrue(initial_otp.is_used)

        new_otp = EmailVerificationOTP.objects.filter(email='resend@example.com', is_used=False).first()
        self.assertIsNotNone(new_otp)
        self.assertNotEqual(initial_otp.id, new_otp.id)

    def test_login_logout(self):
        login_resp = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'Password123!',
        })
        self.assertEqual(login_resp.status_code, 302)

        logout_resp = self.client.get(reverse('accounts:logout'))
        self.assertEqual(logout_resp.status_code, 302)

    def test_address_management(self):
        self.client.login(username='testuser', password='Password123!')
        add_resp = self.client.post(reverse('accounts:address_add'), {
            'full_name': 'Test Recipient',
            'phone': '9876543210',
            'address_line_1': '123 Fashion Street',
            'address_line_2': 'Apt 4B',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'postal_code': '400001',
            'country': 'India',
            'is_default': True,
        })
        self.assertEqual(add_resp.status_code, 302)
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)
        addr = Address.objects.get(user=self.user)
        self.assertTrue(addr.is_default)
        self.assertIn('123 Fashion Street', addr.get_full_address())
