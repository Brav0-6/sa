from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg

# Brand Model: For organizing products by brand
class Brand(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brand_logos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# Category Model: For organizing products into categories
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

# Product Model: For storing product details
class Product(models.Model):
    FABRIC_CHOICES = (
        ('cotton', 'Cotton'),
        ('silk', 'Silk'),
        ('linen', 'Linen'),
        ('chiffon', 'Chiffon'),
        ('georgette', 'Georgette'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='product_images/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    stock = models.PositiveIntegerField(default=0)
    fabric_type = models.CharField(max_length=20, choices=FABRIC_CHOICES, default='other')
    is_featured = models.BooleanField(default=False)
    on_sale = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # If sale price is set, make sure on_sale is True
        if self.sale_price is not None and self.sale_price > 0:
            self.on_sale = True
        super().save(*args, **kwargs)

    def get_current_price(self):
        """Returns the sale price if on sale, otherwise the regular price"""
        if self.on_sale and self.sale_price:
            return self.sale_price
        return self.price
        
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.on_sale and self.sale_price and self.price > 0:
            discount = self.price - self.sale_price
            percentage = (discount / self.price) * 100
            return int(percentage)
        return 0
    
    @property
    def average_rating(self):
        """Calculate average rating for the product"""
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0
    
    @property
    def total_reviews(self):
        """Count total reviews for the product"""
        return self.reviews.count()

    def __str__(self):
        return self.name

# ProductImage: Additional images for product gallery
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='product_gallery/')
    
    def __str__(self):
        return f"Image for {self.product.name}"

# Review Model: For storing product reviews and ratings
class Review(models.Model):
    RATING_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=100)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username}'s {self.rating}-star review on {self.product.name}"

# UserProfile Model: Extends the default User model for additional information
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.user.username

# Cart Model: For storing user's cart items
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} ({self.quantity}) in {self.user.username}'s cart"

    @property
    def total_price(self):
        return self.quantity * self.product.get_current_price()

    class Meta:
        unique_together = ('user', 'product')

# Order Model: For storing order information
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_method = models.CharField(max_length=100, blank=True, null=True, help_text="The shipping rate or method used for this order")
    
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def get_tracking_url(self):
        """Returns the tracking URL if available, or a generic URL based on the tracking number"""
        if self.tracking_url:
            return self.tracking_url
        elif self.tracking_number and self.status != 'pending' and self.status != 'cancelled':
            # Generic tracking URL based on tracking number
            return f"https://www.indiapost.gov.in/_layouts/15/DOP.Portal.Tracking/TrackConsignment.aspx?ConsignmentNo={self.tracking_number}"
        return None

# OrderItem Model: For storing individual items in an order
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of purchase
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order #{self.order.id}"
    
    @property
    def total_price(self):
        return self.price * self.quantity

# Wishlist Model: For storing user's wishlist items
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_date']

    def __str__(self):
        return f"{self.user.username}'s wishlist - {self.product.name}"

# Message Model: For contact form messages from users
class Message(models.Model):
    STATUS_CHOICES = (
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
    )
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_at']

# ShippingConfig Model: For global shipping settings
class ShippingConfig(models.Model):
    """Global shipping configuration settings"""
    enable_free_shipping = models.BooleanField(default=False, 
        help_text="If enabled, all orders will have free shipping regardless of amount")
    free_shipping_min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=999.00,
        help_text="Minimum order amount to qualify for free shipping")
    default_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=60.00,
        help_text="Default shipping cost when no specific rates apply")
    enable_location_based_shipping = models.BooleanField(default=True,
        help_text="Enable location-based shipping rates")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Global Shipping Configuration"

# ShippingRate Model: For setting shipping rates based on location/pincode
class ShippingRate(models.Model):
    RATE_TYPE_CHOICES = (
        ('nationwide', 'Nationwide'),
        ('regional', 'Regional'),
        ('city', 'City'),
        ('pincode', 'Pincode'),
        ('pincode_range', 'Pincode Range'),
    )
    
    name = models.CharField(max_length=100)
    rate_type = models.CharField(max_length=20, choices=RATE_TYPE_CHOICES, default='nationwide')
    country = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    pincode_from = models.CharField(max_length=10, blank=True, null=True, help_text="Start of pincode range")
    pincode_to = models.CharField(max_length=10, blank=True, null=True, help_text="End of pincode range")
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    is_free = models.BooleanField(default=False, help_text="If checked, shipping will be free regardless of cost")
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Minimum order amount for this rate to apply")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rate_type', 'country', 'region', 'cost']
        verbose_name = 'Shipping Rate'
        verbose_name_plural = 'Shipping Rates'

    def __str__(self):
        if self.rate_type == 'nationwide':
            location_str = 'Nationwide'
        elif self.rate_type == 'regional' and self.region:
            location_str = f"{self.region}, {self.country or 'Global'}"
        elif self.rate_type == 'city' and self.city:
            location_str = f"{self.city}, {self.region or ''}, {self.country or 'Global'}"
        elif self.rate_type == 'pincode' and self.pincode:
            location_str = f"Pincode: {self.pincode}"
        elif self.rate_type == 'pincode_range' and self.pincode_from and self.pincode_to:
            location_str = f"Pincodes: {self.pincode_from}-{self.pincode_to}"
        else:
            location_str = 'Global'
        
        return f"{self.name} - {location_str} ({'FREE' if self.is_free else f'₹{self.cost}'})"

