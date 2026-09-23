from django.urls import path

from . import views

app_name = "bakery"

urlpatterns = [
    path("", views.home, name="home"),
    path("about-us/", views.about_us, name="about_us"),
    path("menu/", views.menu, name="menu"),
    path("menu-highlights/", views.menu_highlights, name="menu_highlights"),
    path("gallery/", views.gallery, name="gallery"),
    path("testimonials/", views.testimonials, name="testimonials"),
    path("order-now/", views.order_now, name="order_now"),
    path("contact-us/", views.contact_us, name="contact_us"),
    path("management/", views.management_dashboard, name="dashboard"),
    path("management/menu/", views.management_cake_menu, name="cake_menu"),
    path("management/menu/add/", views.management_cake_create, name="cake_create"),
    path("management/menu/<int:cake_id>/edit/", views.management_cake_edit, name="cake_edit"),
    path("management/orders/", views.management_order_list, name="order_list"),
    path("management/orders/<int:order_id>/update/", views.management_order_update, name="order_update"),
    path("management/orders/<int:order_id>/bill/", views.management_bill_detail, name="bill_detail"),
    path("management/orders/<int:order_id>/bill/pdf/", views.management_bill_pdf, name="bill_pdf"),
    path("management/sales/", views.management_sales_report, name="sales_report"),
]
