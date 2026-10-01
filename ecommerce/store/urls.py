from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("register/", views.register, name="register"),
    path("login/", LoginView.as_view(template_name="store/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/products/", views.DashProductList.as_view(), name="dash_products"),
    path("dashboard/products/add/", views.DashProductCreate.as_view(), name="dash_product_add"),
    path("dashboard/products/<int:pk>/edit/", views.DashProductUpdate.as_view(), name="dash_product_edit"),
    path("dashboard/products/<int:pk>/delete/", views.DashProductDelete.as_view(), name="dash_product_delete"),
    path("dashboard/orders/", views.dash_orders, name="dash_orders"),
    path("dashboard/orders/<int:pk>/status/", views.order_status, name="order_status"),
]
