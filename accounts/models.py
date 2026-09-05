import secrets
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class EmailVerificationOTP(models.Model):
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Email Verification OTP'
        verbose_name_plural = 'Email Verification OTPs'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.email} ({'Used' if self.is_used else 'Active'})"

    @classmethod
    def generate_otp(cls, email, validity_minutes=10):
        # Invalidate previous unused OTPs for this email
        cls.objects.filter(email__iexact=email, is_used=False).update(is_used=True)
        # Generate cryptographically secure 6-digit number
        otp = f"{secrets.randbelow(900000) + 100000}"
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)
        return cls.objects.create(
            email=email.strip().lower(),
            otp_code=otp,
            expires_at=expires_at,
            attempts=0,
            is_used=False
        )

    def is_valid(self, entered_code, max_attempts=5):
        if self.is_used:
            return False, "This verification code has already been used."
        if timezone.now() > self.expires_at:
            return False, "This verification code has expired. Please request a new one."
        if self.attempts >= max_attempts:
            return False, "Too many failed attempts. Please request a new code."
        if self.otp_code.strip() != str(entered_code).strip():
            self.attempts += 1
            self.save(update_fields=['attempts'])
            remaining = max_attempts - self.attempts
            if remaining > 0:
                return False, f"Incorrect verification code. {remaining} attempt(s) remaining."
            else:
                return False, "Too many failed attempts. Please request a new code."
        return True, "Valid"

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        elif not Address.objects.filter(user=self.user).exclude(pk=self.pk).exists():
            self.is_default = True
        super().save(*args, **kwargs)

    def get_full_address(self):
        parts = [self.full_name, self.address_line_1]
        if self.address_line_2:
            parts.append(self.address_line_2)
        parts.extend([f"{self.city}, {self.state} {self.postal_code}", self.country])
        return ", ".join(parts)

    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.postal_code}"
