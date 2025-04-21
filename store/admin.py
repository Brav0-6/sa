from django.contrib import admin
from .models import Product, Category, Brand, UserProfile, Cart, Order, OrderItem, Wishlist, ProductImage, Review, Message, ShippingConfig, ShippingRate

# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_featured')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_featured',)
    search_fields = ('name',)

# Brand Admin
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Product Image Inline
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'sale_price', 'on_sale', 'stock', 'is_featured')
    list_filter = ('category', 'brand', 'on_sale', 'is_featured', 'fabric_type')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'sale_price', 'on_sale', 'stock', 'is_featured')
    inlines = [ProductImageInline]

# Review Admin
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'title', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user', 'product')

# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'state')
    search_fields = ('user__username', 'phone', 'address', 'city', 'state', 'pincode')

# Cart Admin
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'total_price', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'product__name')

# Order Item Inline
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')

# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'total_amount', 'payment_method', 'status', 'order_date')
    list_filter = ('status', 'payment_method', 'payment_status', 'order_date')
    search_fields = ('user__username', 'full_name', 'email', 'phone')
    readonly_fields = ('order_date', 'updated_at')
    list_editable = ('status',)
    inlines = [OrderItemInline]

# Order Item Admin
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'product__name')

# Wishlist Admin
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'added_date')
    list_filter = ('added_date',)
    search_fields = ('user__username', 'product__name')

# Message Admin
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)

# ShippingConfig Admin
@admin.register(ShippingConfig)
class ShippingConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'enable_free_shipping', 'free_shipping_min_amount', 'default_shipping_cost', 'enable_location_based_shipping')
    list_editable = ('enable_free_shipping', 'free_shipping_min_amount', 'default_shipping_cost', 'enable_location_based_shipping')

# ShippingRate Admin
@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate_type', 'region', 'city', 'pincode', 'cost', 'is_active', 'is_free')
    list_filter = ('rate_type', 'is_active', 'is_free')
    search_fields = ('name', 'region', 'city', 'pincode')
    list_editable = ('cost', 'is_active', 'is_free')
