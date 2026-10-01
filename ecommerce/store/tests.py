from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Order, Product


class ShopFlowTests(TestCase):
    def setUp(self):
        self.p = Product.objects.create(name="Shoes", price=999, stock=5)
        self.user = User.objects.create_user("ravi", password="pass12345")
        self.staff = User.objects.create_user("boss", password="pass12345", is_staff=True)

    def test_buy_now_requires_login(self):
        r = self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": 1, "buy_now": 1}, follow=True)
        self.assertEqual(r.redirect_chain[-1][0], "/login/?next=/checkout/")

    def test_full_purchase(self):
        self.client.login(username="ravi", password="pass12345")
        self.client.post(reverse("add_to_cart", args=[self.p.pk]), {"quantity": 2})
        r = self.client.post(reverse("checkout"), {"full_name": "Ravi", "phone": "9999999999", "address": "Delhi"})
        self.assertEqual(r.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 3)
        self.assertEqual(Order.objects.get().total, 1998)

    def test_dashboard_blocked_for_normal_user(self):
        self.client.login(username="ravi", password="pass12345")
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 302)

    def test_staff_crud(self):
        self.client.login(username="boss", password="pass12345")
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.client.post(reverse("dash_product_add"), {"name": "Cap", "description": "", "price": "199", "stock": 10})
        cap = Product.objects.get(name="Cap")
        self.client.post(reverse("dash_product_edit", args=[cap.pk]), {"name": "Cap2", "description": "", "price": "150", "stock": 9})
        cap.refresh_from_db()
        self.assertEqual(cap.name, "Cap2")
        self.client.post(reverse("dash_product_delete", args=[cap.pk]))
        self.assertFalse(Product.objects.filter(pk=cap.pk).exists())
        self.assertEqual(self.client.get(reverse("dash_orders")).status_code, 200)

    def test_logout_and_register(self):
        r = self.client.post(reverse("register"), {"username": "new", "email": "a@b.com", "password1": "Str0ngPass!9", "password2": "Str0ngPass!9"})
        self.assertEqual(r.status_code, 302)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("my_orders")).status_code, 302)
