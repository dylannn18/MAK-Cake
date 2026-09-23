from django import forms

from .models import Bill, Cake, Inventory, Order, SaleRecord


class OrderCreateForm(forms.Form):
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=20)
    cake = forms.ModelChoiceField(queryset=Cake.objects.none(), empty_label="Select a cake")
    quantity = forms.IntegerField(min_value=1, initial=1)
    delivery_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    message = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cake"].queryset = Cake.objects.filter(is_active=True).order_by("name")


class CakeForm(forms.ModelForm):
    class Meta:
        model = Cake
        fields = ["name", "flavor", "description", "unit_price", "is_active", "image_url"]


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["quantity_available", "reorder_level"]


class OrderUpdateForm(forms.Form):
    status = forms.ChoiceField(choices=Order.Status.choices)
    payment_status = forms.ChoiceField(choices=Bill.PaymentStatus.choices)
    payment_method = forms.ChoiceField(choices=SaleRecord.PaymentMethod.choices)
