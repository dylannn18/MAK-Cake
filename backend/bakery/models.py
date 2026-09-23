from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Cake(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    flavor = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Inventory(TimeStampedModel):
    cake = models.OneToOneField(Cake, on_delete=models.CASCADE, related_name="inventory")
    quantity_available = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)

    @property
    def needs_restock(self):
        return self.quantity_available <= self.reorder_level

    def __str__(self):
        return f"{self.cake.name}: {self.quantity_available}"


class Customer(TimeStampedModel):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PREPARING = "preparing", "Preparing"
        DISPATCHED = "dispatched", "Dispatched"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    order_date = models.DateField(default=timezone.localdate)
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def recalculate_totals(self):
        subtotal = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        tax_amount = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total_amount = subtotal + tax_amount
        self.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    def __str__(self):
        return f"Order #{self.id} - {self.customer.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    cake = models.ForeignKey(Cake, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if self.unit_price is None:
            self.unit_price = self.cake.unit_price
        self.line_total = (self.unit_price * self.quantity).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
        self.order.recalculate_totals()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.recalculate_totals()

    def __str__(self):
        return f"{self.cake.name} x {self.quantity}"


class Bill(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIAL = "partial", "Partial"
        PAID = "paid", "Paid"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="bill")
    bill_number = models.CharField(max_length=30, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=15, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return self.bill_number


class SaleRecord(TimeStampedModel):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="sale")
    sold_at = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-sold_at"]

    def __str__(self):
        return f"Sale for Order #{self.order_id}"
