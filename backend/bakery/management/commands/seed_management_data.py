import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from bakery.models import Bill, Cake, Customer, Inventory, Order, OrderItem, SaleRecord


CAKE_DATA = [
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

CAKE_IMAGE_MAP = {
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

CUSTOMER_DATA = [
    ("Aarav Mehta", "aarav@example.com", "9000000001"),
    ("Diya Kapoor", "diya@example.com", "9000000002"),
    ("Kabir Sharma", "kabir@example.com", "9000000003"),
    ("Isha Verma", "isha@example.com", "9000000004"),
    ("Rohan Gupta", "rohan@example.com", "9000000005"),
    ("Meera Nair", "meera@example.com", "9000000006"),
]


class Command(BaseCommand):
    help = "Seed backend management data (cakes, inventory, customers, orders, bills, sales)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--orders",
            type=int,
            default=12,
            help="Number of sample orders to create when no orders exist (default: 12).",
        )
        parser.add_argument(
            "--append-orders",
            action="store_true",
            help="Append orders even if orders already exist.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        orders_to_create = max(options["orders"], 0)
        append_orders = options["append_orders"]
        rng = random.Random(2026)

        cakes_created = self._seed_cakes()
        customers_created = self._seed_customers()
        orders_created = self._seed_orders(rng, orders_to_create, append_orders)

        self.stdout.write(self.style.SUCCESS("Seed completed."))
        self.stdout.write(f"Cakes created: {cakes_created}")
        self.stdout.write(f"Customers created: {customers_created}")
        self.stdout.write(f"Orders created: {orders_created}")

    def _seed_cakes(self):
        created_count = 0
        for name, flavor, price in CAKE_DATA:
            image_url = CAKE_IMAGE_MAP.get(name, "")
            cake, created = Cake.objects.get_or_create(
                name=name,
                defaults={
                    "flavor": flavor,
                    "unit_price": price,
                    "is_active": True,
                    "image_url": image_url,
                },
            )
            if created:
                created_count += 1
            else:
                changed = False
                if not cake.flavor:
                    cake.flavor = flavor
                    changed = True
                if cake.image_url != image_url:
                    cake.image_url = image_url
                    changed = True
                if changed:
                    cake.save(update_fields=["flavor", "image_url", "updated_at"])

            Inventory.objects.get_or_create(
                cake=cake,
                defaults={"quantity_available": 30, "reorder_level": 5},
            )
        return created_count

    def _seed_customers(self):
        created_count = 0
        for full_name, email, phone in CUSTOMER_DATA:
            _, created = Customer.objects.get_or_create(
                phone=phone,
                defaults={"full_name": full_name, "email": email},
            )
            if created:
                created_count += 1
        return created_count

    def _seed_orders(self, rng, orders_to_create, append_orders):
        if orders_to_create == 0:
            return 0
        if Order.objects.exists() and not append_orders:
            return 0

        cakes = list(Cake.objects.filter(is_active=True))
        customers = list(Customer.objects.all())
        if not cakes or not customers:
            return 0

        statuses = [
            Order.Status.PENDING,
            Order.Status.CONFIRMED,
            Order.Status.PREPARING,
            Order.Status.DISPATCHED,
            Order.Status.DELIVERED,
        ]
        created_count = 0
        today = timezone.localdate()

        for i in range(orders_to_create):
            cake = rng.choice(cakes)
            customer = customers[i % len(customers)]
            quantity = rng.randint(1, 3)
            status = rng.choice(statuses)
            order_date = today - timedelta(days=rng.randint(0, 20))
            delivery_date = order_date + timedelta(days=rng.randint(1, 4))

            order = Order.objects.create(
                customer=customer,
                status=status,
                order_date=order_date,
                delivery_date=delivery_date,
                notes="Sample seeded order for backend management.",
            )
            OrderItem.objects.create(
                order=order,
                cake=cake,
                quantity=quantity,
                unit_price=cake.unit_price,
            )

            inventory = Inventory.objects.filter(cake=cake).first()
            if inventory:
                inventory.quantity_available = max(inventory.quantity_available - quantity, 0)
                inventory.save(update_fields=["quantity_available", "updated_at"])

            payment_status = Bill.PaymentStatus.PAID if status == Order.Status.DELIVERED else Bill.PaymentStatus.UNPAID
            bill = Bill.objects.create(
                order=order,
                bill_number=f"BILL-{order.id:05d}",
                due_date=delivery_date,
                payment_status=payment_status,
                paid_at=timezone.now() if payment_status == Bill.PaymentStatus.PAID else None,
            )

            if bill.payment_status == Bill.PaymentStatus.PAID:
                SaleRecord.objects.get_or_create(
                    order=order,
                    defaults={
                        "payment_method": rng.choice(
                            [
                                SaleRecord.PaymentMethod.CASH,
                                SaleRecord.PaymentMethod.UPI,
                                SaleRecord.PaymentMethod.CARD,
                            ]
                        ),
                        "amount_received": order.total_amount,
                    },
                )
            created_count += 1
        return created_count
