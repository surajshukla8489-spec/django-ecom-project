from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CheckoutForm, ProductForm, RegisterForm
from .models import Order, OrderItem, Product


# ---------- helpers ----------
def is_staff(user):
    return user.is_authenticated and user.is_staff


staff_required = user_passes_test(is_staff, login_url="login")


class StaffMixin(UserPassesTestMixin):
    login_url = "login"

    def test_func(self):
        return is_staff(self.request.user)


def get_cart(request):
    cart = request.session.get("cart", {})
    items, total = [], Decimal("0")
    for pid, qty in cart.items():
        product = Product.objects.filter(pk=pid).first()
        if not product:
            continue
        subtotal = product.price * qty
        items.append({"product": product, "quantity": qty, "subtotal": subtotal})
        total += subtotal
    return items, total


# ---------- public store ----------
def home(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, "store/home.html", {"products": products, "q": q})


def product_detail(request, pk):
    return render(request, "store/product_detail.html", {"product": get_object_or_404(Product, pk=pk)})


@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        qty = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        qty = 1
    if product.stock < 1:
        messages.error(request, "Ye product out of stock hai.")
        return redirect("product_detail", pk=pk)
    cart = request.session.get("cart", {})
    cart[str(pk)] = min(cart.get(str(pk), 0) + qty, product.stock)
    request.session["cart"] = cart
    request.session.modified = True
    if "buy_now" in request.POST:
        return redirect("checkout")  # checkout login_required hai -> login maangega
    messages.success(request, f"{product.name} cart me add ho gaya.")
    return redirect("cart")


def cart_view(request):
    items, total = get_cart(request)
    return render(request, "store/cart.html", {"items": items, "total": total})


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = request.session.get("cart", {})
    try:
        qty = int(request.POST.get("quantity", 1))
    except ValueError:
        qty = 1
    if qty < 1:
        cart.pop(str(pk), None)
    else:
        cart[str(pk)] = min(qty, product.stock)
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


@require_POST
def remove_from_cart(request, pk):
    cart = request.session.get("cart", {})
    cart.pop(str(pk), None)
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


@login_required
def checkout(request):
    items, total = get_cart(request)
    if not items:
        messages.info(request, "Aapka cart khali hai.")
        return redirect("cart")
    form = CheckoutForm(request.POST or None,
                        initial={"full_name": request.user.get_full_name() or request.user.username})
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.total = total
                order.save()
                for it in items:
                    product = Product.objects.select_for_update().get(pk=it["product"].pk)
                    if product.stock < it["quantity"]:
                        raise ValueError(f"'{product.name}' ka stock kam hai (bacha: {product.stock}).")
                    product.stock -= it["quantity"]
                    product.save(update_fields=["stock"])
                    OrderItem.objects.create(order=order, product=product, name=product.name,
                                             price=product.price, quantity=it["quantity"])
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("cart")
        request.session["cart"] = {}
        return render(request, "store/order_success.html", {"order": order})
    return render(request, "store/checkout.html", {"form": form, "items": items, "total": total})


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "store/my_orders.html", {"orders": orders})


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account ban gaya, welcome!")
        return redirect("home")
    return render(request, "store/register.html", {"form": form})


# ---------- admin dashboard (staff only) ----------
@staff_required
def dashboard(request):
    revenue = Order.objects.exclude(status="Cancelled").aggregate(s=Sum("total"))["s"] or 0
    ctx = {
        "product_count": Product.objects.count(),
        "order_count": Order.objects.count(),
        "user_count": User.objects.count(),
        "revenue": revenue,
        "recent_orders": Order.objects.select_related("user")[:5],
        "low_stock": Product.objects.filter(stock__lte=5)[:5],
    }
    return render(request, "store/dashboard.html", ctx)


class DashProductList(StaffMixin, ListView):
    model = Product
    template_name = "store/dash_products.html"
    context_object_name = "products"


class DashProductCreate(StaffMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "store/product_form.html"
    success_url = reverse_lazy("dash_products")

    def form_valid(self, form):
        messages.success(self.request, "Product add ho gaya.")
        return super().form_valid(form)


class DashProductUpdate(StaffMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "store/product_form.html"
    success_url = reverse_lazy("dash_products")

    def form_valid(self, form):
        messages.success(self.request, "Product update ho gaya.")
        return super().form_valid(form)


class DashProductDelete(StaffMixin, DeleteView):
    model = Product
    template_name = "store/product_confirm_delete.html"
    success_url = reverse_lazy("dash_products")

    def form_valid(self, form):
        messages.success(self.request, "Product delete ho gaya.")
        return super().form_valid(form)


@staff_required
def dash_orders(request):
    orders = Order.objects.select_related("user").prefetch_related("items")
    return render(request, "store/dash_orders.html", {"orders": orders, "statuses": Order.STATUS_CHOICES})


@staff_required
@require_POST
def order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get("status")
    if status in dict(Order.STATUS_CHOICES):
        order.status = status
        order.save(update_fields=["status"])
        messages.success(request, f"Order #{order.pk} ka status {status} ho gaya.")
    return redirect("dash_orders")
