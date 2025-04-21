from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Pages
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),

    # Messages
    path('my-messages/', views.my_messages_view, name='my_messages'),
    path('delete-message/<int:message_id>/', views.delete_message_view, name='delete_message'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),

    # Product
    path('product/<int:product_id>/', views.product_detail_view, name='product_detail'),
    path('add-product/', views.add_product_view, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product_view, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product_view, name='delete_product'),
    path('category/<slug:category_slug>/', views.category_view, name='category'),
    path('search/', views.search_view, name='search'),

    # Cart
    path('add-to-cart/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('view-cart/', views.view_cart_view, name='view_cart'),
    path('remove-from-cart/<int:cart_item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('update-cart-quantity/', views.update_cart_quantity, name='update_cart_quantity'),
    path('update-shipping-method/', views.update_shipping_method, name='update_shipping_method'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:wishlist_item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Reviews
    path('edit-review/<int:review_id>/', views.edit_review_view, name='edit_review'),
    path('delete-review/<int:review_id>/', views.delete_review_view, name='delete_review'),

    # Orders
    path('checkout/', views.buy_product_view, name='buy_product'),
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail'),

    # Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-products/', views.admin_products_view, name='admin_products'),
    path('admin-categories/', views.admin_categories_view, name='admin_categories'),
    path('admin-orders/', views.admin_orders_view, name='admin_orders'),
    path('admin-users/', views.admin_users_view, name='admin_users'),
    path('admin-reviews/', views.admin_reviews_view, name='admin_reviews'),
    
    # Admin Messages
    path('admin-messages/', views.admin_messages_view, name='admin_messages'),
    path('update-message-status/<int:message_id>/', views.update_message_status_view, name='update_message_status'),
    
    # Admin Shipping Config
    path('admin-shipping-config/', views.admin_shipping_config_view, name='admin_shipping_config'),
    path('update-shipping-config/', views.admin_shipping_config_view, name='update_shipping_config'),
    path('manage-shipping-rate/', views.manage_shipping_rate_view, name='add_shipping_rate'),
    path('manage-shipping-rate/<int:rate_id>/', views.manage_shipping_rate_view, name='edit_shipping_rate'),
    path('delete-shipping-rate/<int:rate_id>/', views.delete_shipping_rate_view, name='delete_shipping_rate'),

    # Shipping Configuration URLs
    path('admin/categories/delete/<int:cat_id>/', views.delete_category_view, name='delete_category'),
    path('admin/shipping/', views.shipping_config_view, name='shipping_config'),
    path('admin/shipping/rate/add/', views.shipping_rate_add_view, name='add_shipping_rate'),
    path('admin/shipping/rate/edit/<int:rate_id>/', views.shipping_rate_edit_view, name='edit_shipping_rate'),
    path('admin/shipping/rate/delete/<int:rate_id>/', views.shipping_rate_delete_view, name='delete_shipping_rate'),
    path('admin/shipping/rate/toggle/<int:rate_id>/', views.shipping_rate_toggle_view, name='toggle_shipping_rate'),
]
