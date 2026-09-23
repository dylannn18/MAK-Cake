from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import CakeForm, InventoryForm, OrderCreateForm, OrderUpdateForm
from .models import Bill, Cake, Customer, Inventory, Order, OrderItem, SaleRecord


DEFAULT_CAKES = [
    ("Chocolate Cake", "Chocolate", Decimal("650.00")),
    ("Red Velvet Cake", "Red Velvet", Decimal("750.00")),
    ("Black Mixed Fruit Cake", "Fruit", Decimal("780.00")),
    ("Gluten-Free Almond Cake", "Almond", Decimal("890.00")),
    ("Fondant Cake", "Fondant", Decimal("950.00")),
    ("Butterscotch Cake", "Butterscotch", Decimal("700.00")),
    ("Vanilla Cake", "Vanilla", Decimal("600.00")),
    ("Blueberry Cake", "Blueberry", Decimal("760.00")),
    ("Mango Cake", "Mango", Decimal("720.00")),
    ("Pinata Cake", "Pinata", Decimal("1100.00")),
    ("Bento Cakes", "Mini", Decimal("450.00")),
    ("Photo Cake", "Custom", Decimal("980.00")),
    ("Hazelnut Praline Cake", "Hazelnut", Decimal("860.00")),
    ("Rasmalai Cake", "Fusion", Decimal("820.00")),
]

DEFAULT_CAKE_IMAGES = {
    "Chocolate Cake": "/static/CHOCOLATE.JPEG",
    "Red Velvet Cake": "/static/RED.JPEG",
    "Black Mixed Fruit Cake": "/static/MIXED.JPEG",
    "Gluten-Free Almond Cake": "/static/ALMOND.JPEG",
    "Fondant Cake": "/static/FONDANT.JPEG",
    "Butterscotch Cake": "/static/BUTTERSCOTCH.JPEG",
    "Vanilla Cake": "/static/VANILLA.JPEG",
    "Blueberry Cake": "/static/BLUEBERRY.WEBP",
    "Mango Cake": "/static/MANGO.JPEG",
    "Pinata Cake": "/static/PINATA.JPEG",
    "Bento Cakes": "/static/BENTO.JPEG",
    "Photo Cake": "/static/PHOTO.WEBP",
    "Hazelnut Praline Cake": "/static/HAZELNUT.JPEG",
    "Rasmalai Cake": "/static/RASMALAI.JPEG",
}


def ensure_cakes_seeded():
    if not Cake.objects.exists():
        Cake.objects.bulk_create(
            [
                Cake(
                    name=name,
                    slug=slugify(name),
                    flavor=flavor,
                    unit_price=price,
                    is_active=True,
                )
                for name, flavor, price in DEFAULT_CAKES
            ]
        )
    for cake in Cake.objects.all():
        if cake.name in DEFAULT_CAKE_IMAGES and cake.image_url != DEFAULT_CAKE_IMAGES[cake.name]:
            cake.image_url = DEFAULT_CAKE_IMAGES[cake.name]
            cake.save(update_fields=["image_url", "updated_at"])
        Inventory.objects.get_or_create(
            cake=cake,
            defaults={"quantity_available": 20, "reorder_level": 5},
        )


def home(request):
    ensure_cakes_seeded()
    return render(request, "site/home.html")


def about_us(request):
    return render(request, "site/about-us.html")


def menu(request):
    ensure_cakes_seeded()
    cakes = Cake.objects.filter(is_active=True).order_by("name")
    return render(request, "site/menu.html", {"cakes": cakes})


def menu_highlights(request):
    return render(request, "site/menu-page.html")


def gallery(request):
    ensure_cakes_seeded()
    gallery_items = Cake.objects.filter(is_active=True).exclude(image_url="").order_by("name")[:12]
    return render(request, "site/gallery.html", {"gallery_items": gallery_items})


def testimonials(request):
    return render(request, "site/testimonials.html")


def contact_us(request):
    return render(request, "site/contact-us.html")


def order_now(request):
    ensure_cakes_seeded()
    if request.method == "POST":
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            cake = form.cleaned_data["cake"]
            qty = form.cleaned_data["quantity"]
            inventory = get_object_or_404(Inventory, cake=cake)
            if inventory.quantity_available < qty:
                form.add_error("quantity", f"Only {inventory.quantity_available} item(s) available in stock.")
            else:
                with transaction.atomic():
                    customer, _ = Customer.objects.get_or_create(
                        phone=form.cleaned_data["phone"],
                        defaults={
                            "full_name": form.cleaned_data["full_name"],
                            "email": form.cleaned_data["email"],
                        },
                    )
                    customer.full_name = form.cleaned_data["full_name"]
                    customer.email = form.cleaned_data["email"]
                    customer.save(update_fields=["full_name", "email", "updated_at"])

                    order = Order.objects.create(
                        customer=customer,
                        status=Order.Status.PENDING,
                        order_date=timezone.localdate(),
                        delivery_date=form.cleaned_data["delivery_date"],
                        notes=form.cleaned_data["message"],
                    )
                    OrderItem.objects.create(
                        order=order,
                        cake=cake,
                        quantity=qty,
                        unit_price=cake.unit_price,
                    )
                    inventory.quantity_available -= qty
                    inventory.save(update_fields=["quantity_available", "updated_at"])
                    Bill.objects.create(
                        order=order,
                        bill_number=f"BILL-{order.id:05d}",
                        due_date=order.delivery_date,
                    )
                messages.success(request, f"Order placed successfully. Your order ID is #{order.id}.")
                return redirect("bakery:order_now")
    else:
        form = OrderCreateForm()

    return render(request, "site/order-now.html", {"form": form})


@staff_member_required
def management_dashboard(request):
    ensure_cakes_seeded()
    revenue = SaleRecord.objects.aggregate(total=Sum("amount_received"))["total"] or Decimal("0.00")
    low_stock = (
        Inventory.objects.select_related("cake")
        .filter(quantity_available__lte=F("reorder_level"))
        .order_by("quantity_available")
    )
    context = {
        "total_cakes": Cake.objects.count(),
        "active_cakes": Cake.objects.filter(is_active=True).count(),
        "total_customers": Customer.objects.count(),
        "total_orders": Order.objects.count(),
        "pending_orders": Order.objects.exclude(status=Order.Status.DELIVERED).count(),
        "recent_orders": Order.objects.select_related("customer")[:8],
        "total_revenue": revenue,
        "low_stock": low_stock[:8],
    }
    return render(request, "bakery/dashboard.html", context)


@staff_member_required
def management_cake_menu(request):
    for cake in Cake.objects.all():
        Inventory.objects.get_or_create(cake=cake, defaults={"quantity_available": 0, "reorder_level": 5})
    cakes = Cake.objects.select_related("inventory").order_by("name")
    return render(request, "bakery/cake_menu.html", {"cakes": cakes})


@staff_member_required
def management_cake_create(request):
    if request.method == "POST":
        cake_form = CakeForm(request.POST)
        inventory_form = InventoryForm(request.POST)
        if cake_form.is_valid() and inventory_form.is_valid():
            cake = cake_form.save()
            inventory = inventory_form.save(commit=False)
            inventory.cake = cake
            inventory.save()
            messages.success(request, "Cake created successfully.")
            return redirect("bakery:cake_menu")
    else:
        cake_form = CakeForm()
        inventory_form = InventoryForm()
    return render(
        request,
        "bakery/cake_form.html",
        {"cake_form": cake_form, "inventory_form": inventory_form, "title": "Add Cake"},
    )


@staff_member_required
def management_cake_edit(request, cake_id):
    cake = get_object_or_404(Cake, id=cake_id)
    inventory, _ = Inventory.objects.get_or_create(cake=cake, defaults={"quantity_available": 0, "reorder_level": 5})
    if request.method == "POST":
        cake_form = CakeForm(request.POST, instance=cake)
        inventory_form = InventoryForm(request.POST, instance=inventory)
        if cake_form.is_valid() and inventory_form.is_valid():
            cake_form.save()
            inventory_form.save()
            messages.success(request, "Cake updated successfully.")
            return redirect("bakery:cake_menu")
    else:
        cake_form = CakeForm(instance=cake)
        inventory_form = InventoryForm(instance=inventory)
    return render(
        request,
        "bakery/cake_form.html",
        {"cake_form": cake_form, "inventory_form": inventory_form, "title": f"Edit {cake.name}"},
    )


@staff_member_required
def management_order_list(request):
    for order in Order.objects.select_related("bill"):
        Bill.objects.get_or_create(
            order=order,
            defaults={"bill_number": f"BILL-{order.id:05d}", "due_date": order.delivery_date},
        )
    orders = Order.objects.select_related("customer", "bill").order_by("-created_at")
    return render(request, "bakery/orders.html", {"orders": orders})


@staff_member_required
def management_order_update(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    bill, _ = Bill.objects.get_or_create(
        order=order,
        defaults={"bill_number": f"BILL-{order.id:05d}", "due_date": order.delivery_date},
    )
    if request.method == "POST":
        form = OrderUpdateForm(request.POST)
        if form.is_valid():
            order.status = form.cleaned_data["status"]
            order.save(update_fields=["status", "updated_at"])

            bill.payment_status = form.cleaned_data["payment_status"]
            if bill.payment_status == Bill.PaymentStatus.PAID and not bill.paid_at:
                bill.paid_at = timezone.now()
            bill.save(update_fields=["payment_status", "paid_at", "updated_at"])

            if bill.payment_status == Bill.PaymentStatus.PAID:
                sale, created = SaleRecord.objects.get_or_create(
                    order=order,
                    defaults={
                        "payment_method": form.cleaned_data["payment_method"],
                        "amount_received": order.total_amount,
                    },
                )
                if not created:
                    sale.payment_method = form.cleaned_data["payment_method"]
                    sale.amount_received = order.total_amount
                    sale.save(update_fields=["payment_method", "amount_received", "updated_at"])
            messages.success(request, f"Order #{order.id} updated.")
    return redirect("bakery:order_list")


@staff_member_required
def management_bill_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related("customer", "bill"), id=order_id)
    bill, _ = Bill.objects.get_or_create(
        order=order,
        defaults={"bill_number": f"BILL-{order.id:05d}", "due_date": order.delivery_date},
    )
    return render(request, "bakery/bill_detail.html", {"order": order, "bill": bill})


@staff_member_required
def management_bill_pdf(request, order_id):
    order = get_object_or_404(Order.objects.select_related("customer", "bill"), id=order_id)
    bill, _ = Bill.objects.get_or_create(
        order=order,
        defaults={"bill_number": f"BILL-{order.id:05d}", "due_date": order.delivery_date},
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "MAK Cakes - Invoice")
    y -= 28

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Bill Number: {bill.bill_number}")
    pdf.drawString(300, y, f"Order ID: #{order.id}")
    y -= 16
    pdf.drawString(40, y, f"Customer: {order.customer.full_name}")
    pdf.drawString(300, y, f"Phone: {order.customer.phone}")
    y -= 16
    pdf.drawString(40, y, f"Issued At: {bill.issued_at:%Y-%m-%d %H:%M}")
    pdf.drawString(300, y, f"Due Date: {bill.due_date or '-'}")
    y -= 16
    pdf.drawString(40, y, f"Payment Status: {bill.get_payment_status_display()}")
    y -= 24

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, y, "Item")
    pdf.drawString(300, y, "Qty")
    pdf.drawString(360, y, "Rate")
    pdf.drawString(440, y, "Total")
    y -= 12
    pdf.line(40, y, width - 40, y)
    y -= 16

    pdf.setFont("Helvetica", 10)
    for item in order.items.all():
        if y < 120:
            pdf.showPage()
            y = height - 50
        pdf.drawString(40, y, item.cake.name[:40])
        pdf.drawRightString(330, y, str(item.quantity))
        pdf.drawRightString(420, y, f"Rs. {item.unit_price}")
        pdf.drawRightString(width - 40, y, f"Rs. {item.line_total}")
        y -= 16

    y -= 6
    pdf.line(320, y, width - 40, y)
    y -= 16
    pdf.drawRightString(width - 40, y, f"Subtotal: Rs. {order.subtotal}")
    y -= 16
    pdf.drawRightString(width - 40, y, f"Tax (5%): Rs. {order.tax_amount}")
    y -= 16
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(width - 40, y, f"Grand Total: Rs. {order.total_amount}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{bill.bill_number}.pdf"'
    return response


@staff_member_required
def management_sales_report(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    sales = SaleRecord.objects.select_related("order", "order__customer").order_by("-sold_at")
    monthly_sales = sales.filter(sold_at__date__gte=month_start)
    total_month_revenue = monthly_sales.aggregate(total=Sum("amount_received"))["total"] or Decimal("0.00")
    total_all_revenue = sales.aggregate(total=Sum("amount_received"))["total"] or Decimal("0.00")

    context = {
        "sales": sales[:40],
        "total_month_revenue": total_month_revenue,
        "total_all_revenue": total_all_revenue,
        "month_start": month_start,
    }
    return render(request, "bakery/sales_report.html", context)
