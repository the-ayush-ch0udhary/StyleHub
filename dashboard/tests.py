from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class DashboardViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff_test',
            password='testpassword123',
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username='normal_test',
            password='testpassword123',
            is_staff=False
        )

    def test_anonymous_redirect(self):
        resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(resp.status_code, 302)

    def test_staff_dashboard_access(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'trendChart')
        self.assertContains(resp, 'statusChart')
        self.assertContains(resp, 'categoryChart')
        self.assertContains(resp, 'paymentChart')
        self.assertContains(resp, 'dashboard-chart-data')
        self.assertContains(resp, 'Paid Revenue')
        self.assertContains(resp, 'Avg Order Value')
