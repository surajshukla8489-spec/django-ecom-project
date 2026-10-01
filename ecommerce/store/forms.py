from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Order, Product


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css


class RegisterForm(BootstrapMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock", "image"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class CheckoutForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "phone", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
