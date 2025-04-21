from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Avg, Count, F
from django.urls import reverse
from .models import Product, Category, Cart, Brand, Order, OrderItem, UserProfile, Wishlist, ProductImage, Review, Message, ShippingConfig, ShippingRate
from .forms import ProductForm, EditProfileForm, ReviewForm, ShippingRateForm, ShippingConfigForm
import json
import random
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
from django.views.decorators.http import require_POST

def home(request):
    """View for the home page showing featured products and categories"""
    # Get featured categories
    featured_categories = Category.objects.filter(is_featured=True)[:3]
    
    # If not enough featured categories, get regular ones
    if featured_categories.count() < 3:
        other_categories = Category.objects.filter(is_featured=False)[:3-featured_categories.count()]
        categories = list(featured_categories) + list(other_categories)
    else:
        categories = featured_categories
    
    # Get featured products
    featured_products = Product.objects.filter(is_featured=True)[:8]
    
    # If not enough featured products, get recent ones
    if featured_products.count() < 8:
        other_products = Product.objects.filter(is_featured=False).order_by('-created_at')[:8-featured_products.count()]
        products = list(featured_products) + list(other_products)
    else:
        products = featured_products
    
    # Get trending products (on sale items or newest products)
    trending_products = Product.objects.filter(on_sale=True)[:8]
    
    # If not enough trending products, get latest products
    if trending_products.count() < 8:
        latest_products = Product.objects.filter(on_sale=False).order_by('-created_at')[:8-trending_products.count()]
        trending_products = list(trending_products) + list(latest_products)
    
    # Get brands for brand slider
    brands = Brand.objects.all()[:5]
    
    return render(request, 'store/home.html', {
        'categories': categories,
        'products': products,
        'trending_products': trending_products,
        'brands': brands
    })

def register_view(request):
    """View for user registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            login(request, user)  # Log user in after register
            messages.success(request, "Your account has been created successfully!")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})

def login_view(request):
    """View for user login"""
    # Default admin credentials
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin123"
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if the credentials match our hardcoded admin login
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Check if admin user exists - if not, create it
            try:
                admin_user = User.objects.get(username=ADMIN_USERNAME)
                # Ensure the user has staff status
                if not admin_user.is_staff or not admin_user.is_superuser:
                    admin_user.is_staff = True
                    admin_user.is_superuser = True
                    admin_user.save()
                
                # Make sure the user has a profile
                try:
                    # Try to get the profile using the related name
                    profile = admin_user.profile
                except UserProfile.DoesNotExist:
                    # Create profile if it doesn't exist
                    UserProfile.objects.create(user=admin_user)
                
            except User.DoesNotExist:
                # Create new admin user with superuser status
                admin_user = User.objects.create_superuser(
                    username=ADMIN_USERNAME,
                    email="admin@example.com",
                    password=ADMIN_PASSWORD
                )
                
                # Create a profile for the admin user
                UserProfile.objects.create(user=admin_user)
            
            # Login the admin user
            login(request, admin_user)
            return redirect('admin_dashboard')
        
        # Normal login flow with Django's form
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Make sure the user has a profile
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(user=user)
                
            login(request, user)
            
            # Redirect admin users to admin dashboard
            if user.is_staff or user.is_superuser:
                return redirect('admin_dashboard')
                
            # Redirect to previous page if available
            next_page = request.GET.get('next')
            if next_page:
                return redirect(next_page)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'store/login.html', {'form': form})

def logout_view(request):
    """View for user logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return render(request, 'store/logout.html')

@login_required
def buy_product_view(request):
    """View for checking out and placing an order"""
    cart_items = Cart.objects.filter(user=request.user)
    
    # Check if cart is empty
    if not cart_items:
        messages.error(request, "Your cart is empty. Add some products before checkout.")
        return redirect('view_cart')
    
    # Calculate cart total
    total_amount = sum(item.total_price for item in cart_items)
    
    if request.method == 'POST':
        # Get order information from the form
        full_name = request.POST.get('full_name', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        
        # Use default values for missing fields or use user profile data
        email = request.user.email  # Use the user's email
        city = request.POST.get('city', 'Default City')
        state = request.POST.get('state', 'Default State')
        pincode = request.POST.get('pincode', '000000')
        payment_method = request.POST.get('payment_method', 'cod')  # Default to COD
        
        # Calculate shipping cost based on address and cart total
        shipping_address = {
            'city': city,
            'state': state,
            'pincode': pincode
        }
        shipping_cost, is_free_shipping = calculate_shipping_cost(
            user=request.user,
            cart_total=total_amount,
            shipping_address=shipping_address
        )
        
        # Add shipping cost to total
        final_total = total_amount + shipping_cost
        
        # Determine shipping method
        if is_free_shipping:
            shipping_method = "Free Shipping"
        else:
            # Try to find a matching shipping rate
            shipping_rate = None
            if shipping_address.get('state'):
                shipping_rate = ShippingRate.objects.filter(
                    rate_type='state',
                    region__iexact=shipping_address['state'],
                    is_active=True
                ).first()
            
            if not shipping_rate and shipping_address.get('city'):
                shipping_rate = ShippingRate.objects.filter(
                    rate_type='city',
                    city__iexact=shipping_address['city'],
                    is_active=True
                ).first()
            
            if not shipping_rate:
                shipping_rate = ShippingRate.objects.filter(
                    rate_type='nationwide',
                    is_active=True
                ).first()
            
            shipping_method = shipping_rate.name if shipping_rate else "Standard Shipping"
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            total_amount=final_total,
            payment_method=payment_method,
            shipping_cost=shipping_cost,
            shipping_method=shipping_method
        )
        
        # Create order items and reduce stock
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.get_current_price()
            )
            
            # Reduce stock
            product = cart_item.product
            product.stock -= cart_item.quantity
            product.save()
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, "Your order has been placed successfully! Order ID: #{}".format(order.id))
        return redirect('home')

    # Get user profile for pre-filling form
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None
    
    # Get shipping address from profile
    shipping_address = {}
    if profile:
        shipping_address = {
            'city': profile.city or '',
            'state': profile.state or '',
            'pincode': profile.pincode or ''
        }
    
    # Calculate shipping fee based on shipping rules
    shipping_cost, is_free_shipping = calculate_shipping_cost(
        user=request.user,
        cart_total=total_amount,
        shipping_address=shipping_address
    )
    
    # Get shipping configuration for threshold
    config, _ = ShippingConfig.objects.get_or_create(
        pk=1, 
        defaults={
            'enable_free_shipping': False,
            'free_shipping_min_amount': 500.00,
            'default_shipping_cost': 50.00,
            'enable_location_based_shipping': False
        }
    )
    
    return render(request, 'store/buy_product.html', {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'shipping_cost': shipping_cost,
        'is_free_shipping': is_free_shipping,
        'final_total': total_amount + shipping_cost,
        'profile': profile,
        'free_shipping_threshold': config.free_shipping_min_amount
    })

@staff_member_required
def add_product_view(request):
    """Admin view for adding a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Begin transaction
                product = form.save(commit=False)
                
                # Explicitly set name from title field in the form
                if 'title' in request.POST:
                    product.name = request.POST.get('title')
                
                # Handle slug creation
                base_slug = slugify(product.name)
                slug = base_slug
                counter = 1
                
                # Make sure slug is unique
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                product.slug = slug
                
                # Handle is_featured field
                product.is_featured = request.POST.get('is_featured') == 'on'
                
                # Set sale price based on form data
                if request.POST.get('on_sale') == 'on' and request.POST.get('sale_price'):
                    product.on_sale = True
                    
                    # Ensure sale_price is a decimal/float
                    try:
                        product.sale_price = float(request.POST.get('sale_price'))
                        
                        # Ensure price is properly compared as numbers
                        if product.sale_price >= float(request.POST.get('price', 0)):
                            messages.error(request, "Sale price must be less than regular price")
                            return render(request, 'store/add_product.html', {
                                'form': form,
                                'categories': Category.objects.all(),
                                'brands': Brand.objects.all()
                            })
                    except (ValueError, TypeError):
                        messages.error(request, "Invalid price format")
                        return render(request, 'store/add_product.html', {
                            'form': form,
                            'categories': Category.objects.all(),
                            'brands': Brand.objects.all()
                        })
                else:
                    product.on_sale = False
                    product.sale_price = None
                
                # Set fabric type
                if 'fabric_type' in request.POST:
                    product.fabric_type = request.POST.get('fabric_type')
                
                # Assign main image to the image field
                if 'main_image' in request.FILES:
                    product.image = request.FILES['main_image']
                
                # Save the product
                product.save()
                
                # Handle additional images
                additional_images = request.FILES.getlist('additional_images')
                if additional_images:
                    for image in additional_images:
                        ProductImage.objects.create(product=product, image=image)
                
                messages.success(request, f'Product "{product.name}" added successfully!')
                return redirect('admin_products')
            except Exception as e:
                messages.error(request, f"Error adding product: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm()
        
    # Get available categories and brands for reference
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    return render(request, 'store/add_product.html', {
        'form': form,
        'categories': categories,
        'brands': brands
    })

@staff_member_required
def edit_product_view(request, product_id):
    """Admin view for editing an existing product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                # Begin transaction
                product = form.save(commit=False)
                
                # Explicitly set name from title field in the form
                if 'title' in request.POST:
                    product.name = request.POST.get('title')
                
                # Handle is_featured field
                product.is_featured = request.POST.get('is_featured') == 'on'
                
                # Set sale price based on form data
                if request.POST.get('on_sale') == 'on' and request.POST.get('sale_price'):
                    product.on_sale = True
                    
                    # Ensure sale_price is a decimal/float
                    try:
                        product.sale_price = float(request.POST.get('sale_price'))
                        
                        # Ensure price is properly compared as numbers
                        if product.sale_price >= float(request.POST.get('price', 0)):
                            messages.error(request, "Sale price must be less than regular price")
                            return render(request, 'store/edit_product.html', {
                                'form': form,
                                'product': product,
                                'additional_images': ProductImage.objects.filter(product=product),
                                'categories': Category.objects.all(),
                                'brands': Brand.objects.all()
                            })
                    except (ValueError, TypeError):
                        messages.error(request, "Invalid price format")
                        return render(request, 'store/edit_product.html', {
                            'form': form,
                            'product': product,
                            'additional_images': ProductImage.objects.filter(product=product),
                            'categories': Category.objects.all(),
                            'brands': Brand.objects.all()
                        })
                else:
                    product.on_sale = False
                    product.sale_price = None
                    
                # Set fabric type
                if 'fabric_type' in request.POST:
                    product.fabric_type = request.POST.get('fabric_type')
                
                # Assign main image to the image field if provided
                if 'main_image' in request.FILES:
                    product.image = request.FILES['main_image']
                
                # Save the product
                product.save()
                
                # Handle additional images
                if 'additional_images' in request.FILES:
                    additional_images = request.FILES.getlist('additional_images')
                    if additional_images:
                        # Remove old additional images if "replace_images" is checked
                        if 'replace_images' in request.POST:
                            ProductImage.objects.filter(product=product).delete()
                            
                        # Add new images
                        for image in additional_images:
                            ProductImage.objects.create(product=product, image=image)
                
                messages.success(request, f'Product "{product.name}" updated successfully!')
                return redirect('admin_products')
            except Exception as e:
                messages.error(request, f"Error updating product: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Pre-fill the form with existing data
        initial_data = {
            'title': product.name,
            'description': product.description,
            'price': product.price,
            'sale_price': product.sale_price if product.on_sale else None,
            'stock': product.stock,
            'category': product.category,
            'brand': product.brand,
            'fabric_type': product.fabric_type,
            'on_sale': product.on_sale,
            'is_featured': product.is_featured,
        }
        form = ProductForm(instance=product, initial=initial_data)
    
    # Get product's additional images
    additional_images = ProductImage.objects.filter(product=product)
    
    # Get available categories and brands for reference
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    return render(request, 'store/edit_product.html', {
        'form': form,
        'product': product,
        'additional_images': additional_images,
        'categories': categories,
        'brands': brands
    })

@staff_member_required
def delete_product_view(request, product_id):
    """Admin view for deleting a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product_name = product.name
        
        # Delete product images to avoid orphaned files
        if product.main_image:
            product.main_image.delete()
        
        # Delete additional images
        additional_images = ProductImage.objects.filter(product=product)
        for img in additional_images:
            img.image.delete()
            
        # Delete the product
        product.delete()
        
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('admin_products')
        
    return render(request, 'store/confirm_delete_product.html', {
        'product': product
    })

@staff_member_required(login_url='login')
def admin_dashboard_view(request):
    """Admin dashboard view - restricted to staff and superusers only"""
    # Double-check that user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access the admin dashboard.")
        return redirect('home')
    
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    revenue = Order.objects.filter(payment_status=True).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Products with lowest stock
    low_stock_products = Product.objects.filter(stock__lt=10).order_by('stock')[:5]
    
    # Recent orders
    recent_orders = Order.objects.order_by('-order_date')[:5]
    
    # Latest users
    latest_users = User.objects.order_by('-date_joined')[:5]
    
    # Best-selling products
    best_sellers = OrderItem.objects.values('product').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]
    best_selling_products = [Product.objects.get(id=item['product']) for item in best_sellers] if best_sellers else []
    
    # Total cart items - for the admin dashboard display
    total_cart_items = Cart.objects.count()

    context = {
        'total_products': total_products,
        'total_users': total_users,
        'total_orders': total_orders,
        'total_cart_items': total_cart_items,
        'revenue': revenue,
        'low_stock_products': low_stock_products,
        'recent_orders': recent_orders,
        'latest_users': latest_users,
        'best_selling_products': best_selling_products
    }
    
    return render(request, 'store/admin_dashboard.html', context)

@staff_member_required(login_url='login')
def admin_products_view(request):
    """Admin products management view - restricted to staff and superusers only"""
    # Double-check that user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access the admin products page.")
        return redirect('home')
    
    # Get all products with sorting options
    sort_by = request.GET.get('sort', 'name')  # Default sort by name
    
    if sort_by == 'price_low':
        products = Product.objects.all().order_by('price')
    elif sort_by == 'price_high':
        products = Product.objects.all().order_by('-price')
    elif sort_by == 'newest':
        products = Product.objects.all().order_by('-created_at')
    elif sort_by == 'stock_low':
        products = Product.objects.all().order_by('stock')
    else:  # Default sort by name
        products = Product.objects.all().order_by('name')
    
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')
    
    # Apply filters if specified
    if category_filter:
        products = products.filter(category__id=category_filter)
    
    if stock_filter == 'low':
        products = products.filter(stock__lt=10)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    
    # Get all categories for the filter dropdown
    categories = Category.objects.all()
    
    # Pagination
    paginator = Paginator(products, 10)  # 10 products per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'sort_by': sort_by,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
        'total_products': products.count(),
    }
    
    return render(request, 'store/admin_products.html', context)

@login_required
def admin_categories_view(request):
    """Admin categories management view - restricted to staff and superusers only"""
    # Double-check that user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access the admin categories page.")
        return redirect('home')
    
    # Process category addition
    if request.method == 'POST' and 'add_category' in request.POST:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_featured = request.POST.get('is_featured') == 'on'
        
        if not name:
            messages.error(request, "Category name is required.")
        else:
            # Create slug from name
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            
            # Make sure slug is unique
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            try:
                # Create new category
                category = Category.objects.create(
                    name=name, 
                    description=description, 
                    slug=slug,
                    is_featured=is_featured
                )
                
                # Handle category image if provided
                if 'image' in request.FILES:
                    category.image = request.FILES['image']
                    category.save()
                
                messages.success(request, f'Category "{name}" added successfully!')
            except Exception as e:
                messages.error(request, f"Error adding category: {str(e)}")
    
    # Process category edit
    elif request.method == 'POST' and 'edit_category' in request.POST:
        category_id = request.POST.get('category_id')
        try:
            category = Category.objects.get(id=category_id)
            
            category.name = request.POST.get('name', '').strip()
            category.description = request.POST.get('description', '').strip()
            category.is_featured = request.POST.get('is_featured') == 'on'
            
            # Handle category image if provided
            if 'image' in request.FILES:
                # Delete old image first
                if category.image:
                    category.image.delete()
                category.image = request.FILES['image']
            
            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
        except Exception as e:
            messages.error(request, f"Error updating category: {str(e)}")
    
    # Process category deletion
    elif request.method == 'POST' and 'delete_category' in request.POST:
        category_id = request.POST.get('category_id')
        try:
            category = Category.objects.get(id=category_id)
            
            # Check if category has associated products
            products_count = Product.objects.filter(category=category).count()
            if products_count > 0:
                messages.error(request, f'Cannot delete category "{category.name}" because it has {products_count} associated products.')
            else:
                # Delete category image if exists
                if category.image:
                    category.image.delete()
                
                category_name = category.name
                category.delete()
                messages.success(request, f'Category "{category_name}" deleted successfully!')
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
        except Exception as e:
            messages.error(request, f"Error deleting category: {str(e)}")
    
    # Get all categories
    categories = Category.objects.all().order_by('name')
    
    # Count products in each category
    for category in categories:
        category.products_count = Product.objects.filter(category=category).count()
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    
    return render(request, 'store/admin_categories.html', context)

@staff_member_required(login_url='login')
def admin_orders_view(request):
    """Admin orders management view - restricted to staff and superusers only"""
    # Double-check that user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access the admin orders page.")
        return redirect('home')
    
    # Get orders with sorting options
    sort_by = request.GET.get('sort', '-order_date')  # Default sort by date (newest first)
    
    if sort_by == 'order_date':
        orders = Order.objects.all().order_by('order_date')  # Oldest first
    elif sort_by == 'total_high':
        orders = Order.objects.all().order_by('-total_amount')  # Highest amount first
    elif sort_by == 'total_low':
        orders = Order.objects.all().order_by('total_amount')  # Lowest amount first
    else:  # Default sort by newest
        orders = Order.objects.all().order_by('-order_date')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    
    # Apply filters if specified
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Process order update
    if request.method == 'POST' and 'update_order' in request.POST:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        
        try:
            order = Order.objects.get(id=order_id)
            order.status = new_status
            
            # If order is marked as delivered, update delivery date
            if new_status == 'D':  # Assuming 'D' is the code for 'Delivered'
                order.delivery_date = timezone.now()
            
            order.save()
            messages.success(request, f'Order #{order_id} status updated successfully!')
        except Order.DoesNotExist:
            messages.error(request, f"Order #{order_id} not found.")
        except Exception as e:
            messages.error(request, f"Error updating order: {str(e)}")
    
    # Pagination
    paginator = Paginator(orders, 15)  # 15 orders per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get totals
    total_orders = Order.objects.count()
    revenue = Order.objects.filter(payment_status=True).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'status_filter': status_filter,
        'total_orders': total_orders,
        'revenue': revenue,
    }
    
    return render(request, 'store/admin_orders.html', context)

@staff_member_required(login_url='login')
def admin_users_view(request):
    """Admin users management view - restricted to staff and superusers only"""
    # Double-check that user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access the admin users page.")
        return redirect('home')
    
    # Get users with sorting options
    sort_by = request.GET.get('sort', '-date_joined')  # Default sort by date joined (newest first)
    
    if sort_by == 'username':
        users = User.objects.all().order_by('username')
    elif sort_by == 'date_joined':
        users = User.objects.all().order_by('date_joined')  # Oldest first
    elif sort_by == 'last_login':
        users = User.objects.all().order_by('-last_login')  # Recent login first
    else:  # Default sort by newest
        users = User.objects.all().order_by('-date_joined')
    
    # Get filter parameters
    is_staff_filter = request.GET.get('is_staff', '')
    is_active_filter = request.GET.get('is_active', '')
    
    # Apply filters if specified
    if is_staff_filter:
        users = users.filter(is_staff=(is_staff_filter == 'yes'))
    
    if is_active_filter:
        users = users.filter(is_active=(is_active_filter == 'yes'))
    
    # Process user status update
    if request.method == 'POST' and 'update_user' in request.POST:
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id)
            
            # Don't allow modifying superuser status for safety
            if user.is_superuser and request.user.id != user.id:
                messages.error(request, f"Cannot modify superuser {user.username}")
            else:
                if action == 'make_staff':
                    user.is_staff = True
                    user.save()
                    messages.success(request, f"User {user.username} is now a staff member.")
                elif action == 'remove_staff':
                    user.is_staff = False
                    user.save()
                    messages.success(request, f"User {user.username} is no longer a staff member.")
                elif action == 'activate':
                    user.is_active = True
                    user.save()
                    messages.success(request, f"User {user.username} has been activated.")
                elif action == 'deactivate':
                    user.is_active = False
                    user.save()
                    messages.success(request, f"User {user.username} has been deactivated.")
        except User.DoesNotExist:
            messages.error(request, f"User not found.")
        except Exception as e:
            messages.error(request, f"Error updating user: {str(e)}")
    
    # Pagination
    paginator = Paginator(users, 15)  # 15 users per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_users = User.objects.count()
    staff_users = User.objects.filter(is_staff=True).count()
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'is_staff_filter': is_staff_filter,
        'is_active_filter': is_active_filter,
        'total_users': total_users,
        'staff_users': staff_users,
    }
    
    return render(request, 'store/admin_users.html', context)

@login_required
def profile_view(request):
    """View for user profile"""
    user = request.user
    profile = UserProfile.objects.get_or_create(user=user)[0]
    orders = Order.objects.filter(user=user).order_by('-order_date')
    wishlist_items = Wishlist.objects.filter(user=user)
    
    # Get the user's messages
    user_messages = Message.objects.filter(user=user).order_by('-created_at')
    
    return render(request, 'store/profile.html', {
        'user': user,
        'profile': profile,
        'orders': orders,
        'wishlist_items': wishlist_items,
        'user_messages': user_messages
    })

@login_required
def edit_profile_view(request):
    """View for editing user profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
        
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            form.save()
            
            # Update profile fields
            profile.phone = request.POST.get('phone', '')
            profile.address = request.POST.get('address', '')
            profile.city = request.POST.get('city', '')
            profile.state = request.POST.get('state', '')
            profile.pincode = request.POST.get('pincode', '')
            
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
                
            profile.save()
            
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
            
    else:
        form = EditProfileForm(instance=request.user)
        
    return render(request, 'store/edit_profile.html', {
        'form': form,
        'profile': profile
    })

def product_detail_view(request, product_id):
    """View for showing product details"""
    product = get_object_or_404(Product, id=product_id)
    
    # Get related products (same category)
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id).order_by('?')[:4]  # 4 random related products
    
    # Get product reviews
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    
    # Check if user has already reviewed this product
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = Review.objects.filter(product=product, user=request.user).exists()
    
    # Initialize review form
    review_form = None
    if request.user.is_authenticated and not user_has_reviewed:
        review_form = ReviewForm()
        
        if request.method == 'POST' and 'review_submit' in request.POST:
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                messages.success(request, "Thank you! Your review has been submitted successfully.")
                return redirect('product_detail', product_id=product.id)
    
    # Get rating statistics
    rating_counts = reviews.values('rating').annotate(count=Sum('rating'))
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_ratings = reviews.count()
    
    for rating in reviews.values('rating'):
        rating_value = int(rating['rating'])
        rating_distribution[rating_value] = rating_distribution.get(rating_value, 0) + 1
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'review_form': review_form,
        'user_has_reviewed': user_has_reviewed,
        'rating_distribution': rating_distribution,
        'total_ratings': total_ratings
    }
    
    return render(request, 'store/product_detail.html', context)

@login_required
def edit_review_view(request, review_id):
    """View for editing a product review"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Your review has been updated successfully.")
            return redirect('product_detail', product_id=review.product.id)
    else:
        form = ReviewForm(instance=review)
    
    return render(request, 'store/edit_review.html', {
        'form': form,
        'review': review
    })

@login_required
def delete_review_view(request, review_id):
    """View for deleting a product review"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if the user is the owner of the review
    if review.user != request.user:
        messages.error(request, "You don't have permission to delete this review.")
        return redirect('product_detail', product_id=review.product.id)
    
    # Delete the review
    review.delete()
    messages.success(request, "Your review has been deleted.")
    
    # Redirect back to the product detail page
    return redirect('product_detail', product_id=review.product.id)

def check_user_login(request, action_type, product_id=None):
    """Helper function to check if user is logged in and prepare auth modal data if not"""
    # Check if user is logged in
    if not request.user.is_authenticated:
        # If it's an AJAX request, return JSON response for modal
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
            product = None
            if product_id:
                product = get_object_or_404(Product, id=product_id)
                
            login_url = f"{reverse('login')}?next={request.META.get('HTTP_REFERER', '/')}"
            register_url = reverse('register')
            
            return JsonResponse({
                'success': False,
                'requires_login': True,
                'action_type': action_type,
                'login_url': login_url,
                'register_url': register_url,
                'product_name': product.name if product else '',
                'product_id': product_id if product_id else '',
            })
        
        # If it's a regular request, redirect to login page
        messages.info(request, f"Please login to {action_type}.")
        return redirect(f"{reverse('login')}?next={request.META.get('HTTP_REFERER', '/')}")
    
    # User is logged in, return None to continue normal flow
    return None

def add_to_cart_view(request, product_id):
    """View for adding a product to cart"""
    # Check if user is logged in
    login_check = check_user_login(request, 'add to cart', product_id)
    if login_check:
        return login_check
    
    product = get_object_or_404(Product, id=product_id)
    
    # Check if product is in stock
    if product.stock <= 0:
        messages.error(request, "This product is out of stock.")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'error': 'Product is out of stock'})
        return redirect('product_detail', product_id=product.id)
    
    # Get quantity from form, JSON or default to 1
    if request.method == 'POST':
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                quantity = int(data.get('quantity', 1))
            except (ValueError, json.JSONDecodeError):
                quantity = 1
        else:
            quantity = int(request.POST.get('quantity', 1))
    else:
        quantity = 1
    
    # Check if quantity exceeds stock
    if quantity > product.stock:
        quantity = product.stock
        messages.warning(request, f"Only {product.stock} items available. We've adjusted your quantity.")
    
    # Add to cart
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    
    if created:
        cart_item.quantity = quantity
    else:
        # For existing cart item, update quantity but don't exceed stock
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock:
            new_quantity = product.stock
            messages.warning(request, f"You now have the maximum available quantity ({product.stock}) in your cart.")
        cart_item.quantity = new_quantity
    
        cart_item.save()
    
    messages.success(request, f"{product.name} added to your cart.")
    
    # Check if request is AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
        cart_count = Cart.objects.filter(user=request.user).count()
        return JsonResponse({
            'success': True, 
            'message': f"{product.name} added to your cart.",
            'cart_count': cart_count
        })
        
    return redirect('view_cart')

@login_required
def view_cart_view(request):
    """View for showing cart items"""
    cart_items = Cart.objects.filter(user=request.user)
    
    # Calculate total
    total = sum(item.total_price for item in cart_items)
    
    # Get user profile for shipping address
    try:
        profile = request.user.profile
        shipping_address = {
            'city': profile.city or '',
            'state': profile.state or '',
            'pincode': profile.pincode or ''
        }
    except UserProfile.DoesNotExist:
        profile = None
        shipping_address = {}

    # Calculate shipping cost based on shipping configuration
    shipping_cost, is_free_shipping = calculate_shipping_cost(
        user=request.user,
        cart_total=total,
        shipping_address=shipping_address
    )
    
    # Get shipping configuration for threshold
    config, _ = ShippingConfig.objects.get_or_create(
        pk=1, 
        defaults={
            'enable_free_shipping': False,
            'free_shipping_min_amount': 500.00,
            'default_shipping_cost': 50.00,
            'enable_location_based_shipping': False
        }
    )
    
    # Get available shipping rates
    available_shipping_rates = []
    
    # Check admin global settings first
    global_shipping_method = None
    
    # If admin has enabled free shipping for all orders
    if config.enable_free_shipping:
        global_shipping_method = {
            'id': 'global_free',
            'name': 'Free Shipping (All Orders)',
            'description': 'Free shipping for all orders as set by admin',
            'cost': 0,
            'is_free': True,
            'is_selected': True,
            'is_disabled': False,
            'is_admin_setting': True
        }
        available_shipping_rates.append(global_shipping_method)
    # If order qualifies for free shipping based on minimum amount
    elif is_free_shipping and total >= config.free_shipping_min_amount:
        global_shipping_method = {
            'id': 'threshold_free',
            'name': 'Free Shipping',
            'description': f'Orders above ₹{config.free_shipping_min_amount} qualify for free shipping',
            'cost': 0,
            'is_free': True,
            'is_selected': True,
            'is_disabled': False,
            'is_admin_setting': True
        }
        available_shipping_rates.append(global_shipping_method)
        
        # Also include standard shipping as an option but not selected
        standard_shipping = {
            'id': 'standard',
            'name': 'Standard Shipping',
            'description': '3-5 business days',
            'cost': config.default_shipping_cost,
            'is_free': False,
            'is_selected': False,
            'is_admin_setting': True
        }
        available_shipping_rates.append(standard_shipping)
    # Default cost shipping as set by admin
    else:
        standard_shipping = {
            'id': 'standard',
            'name': 'Standard Shipping',
            'description': '3-5 business days',
            'cost': config.default_shipping_cost,
            'is_free': False,
            'is_selected': True,
            'is_admin_setting': True
        }
        available_shipping_rates.append(standard_shipping)
        
        # If there's a minimum amount for free shipping, show it as an option but disabled
        if config.free_shipping_min_amount > 0:
            free_shipping = {
                'id': 'free',
                'name': 'Free Shipping',
                'description': f'Add ₹{config.free_shipping_min_amount - total:.2f} more to qualify',
                'cost': 0,
                'is_free': True,
                'is_selected': False,
                'is_disabled': total < config.free_shipping_min_amount,
                'is_admin_setting': True
            }
            available_shipping_rates.append(free_shipping)
    
    # If location-based shipping is enabled, get applicable rates from the database
    if config.enable_location_based_shipping and shipping_address:
        # Get rates based on pincode
        if shipping_address.get('pincode'):
            pincode = shipping_address['pincode']
            
            # Check exact pincode match
            pincode_rates = ShippingRate.objects.filter(
                rate_type='pincode',
                pincode=pincode,
                is_active=True
            )
            
            # Check pincode range
            pincode_range_rates = ShippingRate.objects.filter(
                rate_type='pincode_range',
                is_active=True
            )
            for rate in pincode_range_rates:
                if rate.pincode_from and rate.pincode_to:
                    try:
                        if int(rate.pincode_from) <= int(pincode) <= int(rate.pincode_to):
                            pincode_rates = list(pincode_rates) + [rate]
                    except (ValueError, TypeError):
                        continue
            
            # Add pincode rates to available options
            for rate in pincode_rates:
                # Skip if we already have a global free shipping method
                if global_shipping_method and global_shipping_method['is_free'] and rate.is_free:
                    continue
                    
                rate_option = {
                    'id': f'pincode_{rate.id}',
                    'name': rate.name,
                    'description': f'Special rate for your area',
                    'cost': 0 if rate.is_free else rate.cost,
                    'is_free': rate.is_free,
                    'is_selected': False,
                    'rate_type': 'pincode',
                    'is_admin_setting': False
                }
                available_shipping_rates.append(rate_option)
        
        # Get rates based on city
        if shipping_address.get('city'):
            city_rates = ShippingRate.objects.filter(
                rate_type='city',
                city__iexact=shipping_address['city'],
                is_active=True
            )
            
            for rate in city_rates:
                # Skip if we already have a global free shipping method
                if global_shipping_method and global_shipping_method['is_free'] and rate.is_free:
                    continue
                    
                rate_option = {
                    'id': f'city_{rate.id}',
                    'name': rate.name,
                    'description': f'Delivery to {shipping_address["city"]}',
                    'cost': 0 if rate.is_free else rate.cost,
                    'is_free': rate.is_free,
                    'is_selected': False,
                    'rate_type': 'city',
                    'is_admin_setting': False
                }
                available_shipping_rates.append(rate_option)
        
        # Get rates based on state/region
        if shipping_address.get('state'):
            state_rates = ShippingRate.objects.filter(
                rate_type='regional',
                region__iexact=shipping_address['state'],
                is_active=True
            )
            
            for rate in state_rates:
                # Skip if we already have a global free shipping method
                if global_shipping_method and global_shipping_method['is_free'] and rate.is_free:
                    continue
                    
                rate_option = {
                    'id': f'region_{rate.id}',
                    'name': rate.name,
                    'description': f'Delivery in {shipping_address["state"]}',
                    'cost': 0 if rate.is_free else rate.cost,
                    'is_free': rate.is_free,
                    'is_selected': False,
                    'rate_type': 'region',
                    'is_admin_setting': False
                }
                available_shipping_rates.append(rate_option)
        
        # Get nationwide rates
        nationwide_rates = ShippingRate.objects.filter(
            rate_type='nationwide',
            is_active=True
        )
        
        for rate in nationwide_rates:
            # Skip if we already have a global free shipping method
            if global_shipping_method and global_shipping_method['is_free'] and rate.is_free:
                continue
                
            rate_option = {
                'id': f'nationwide_{rate.id}',
                'name': rate.name,
                'description': 'All India delivery',
                'cost': 0 if rate.is_free else rate.cost,
                'is_free': rate.is_free,
                'is_selected': False,
                'rate_type': 'nationwide',
                'is_admin_setting': False
            }
            available_shipping_rates.append(rate_option)
    
    # Additional context for admin shipping settings
    admin_shipping_settings = {
        'global_free_shipping': config.enable_free_shipping,
        'free_shipping_min_amount': config.free_shipping_min_amount,
        'default_shipping_cost': config.default_shipping_cost,
        'enable_location_based': config.enable_location_based_shipping,
        'qualifies_for_free_shipping': is_free_shipping,
        'amount_needed_for_free': max(0, config.free_shipping_min_amount - total) if not is_free_shipping else 0
    }
    
    return render(request, 'store/view_cart.html', {
        'cart_items': cart_items,
        'total': total,
        'shipping_cost': shipping_cost,
        'is_free_shipping': is_free_shipping,
        'final_total': total + shipping_cost,
        'free_shipping_threshold': config.free_shipping_min_amount,
        'shipping_rates': available_shipping_rates,
        'shipping_config': config,
        'admin_shipping_settings': admin_shipping_settings
    })

@login_required
def remove_from_cart_view(request, cart_item_id):
    """View for removing an item from cart"""
    cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    
    messages.success(request, f"{product_name} removed from your cart.")
    
    # Check if request is AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
        
    return redirect('view_cart')

@login_required
def update_cart_quantity(request):
    """AJAX view for updating cart quantity"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        try:
            cart_item = Cart.objects.get(id=item_id, user=request.user)
            
            # Validate quantity
            if quantity <= 0:
                quantity = 1
            if quantity > cart_item.product.stock:
                quantity = cart_item.product.stock
                
            cart_item.quantity = quantity
            cart_item.save()
            
            # Recalculate cart total
            cart_items = Cart.objects.filter(user=request.user)
            subtotal = sum(item.total_price for item in cart_items)
            
            # Get shipping address from profile
            try:
                profile = request.user.profile
                shipping_address = {
                    'city': profile.city or '',
                    'state': profile.state or '',
                    'pincode': profile.pincode or ''
                }
            except UserProfile.DoesNotExist:
                shipping_address = {}
            
            # Calculate shipping cost
            shipping_cost, is_free_shipping = calculate_shipping_cost(
                user=request.user,
                cart_total=subtotal,
                shipping_address=shipping_address
            )
            
            # Get free shipping threshold
            config, _ = ShippingConfig.objects.get_or_create(
                pk=1, 
                defaults={
                    'enable_free_shipping': False,
                    'free_shipping_min_amount': 500.00,
                    'default_shipping_cost': 50.00,
                    'enable_location_based_shipping': False
                }
            )
            
            # Calculate remaining amount for free shipping
            remaining_for_free = max(0, config.free_shipping_min_amount - subtotal) if not is_free_shipping else 0
            
            # Get available shipping rates
            available_shipping_rates = []
            
            # Always include standard shipping as the default option
            standard_shipping = {
                'id': 'standard',
                'name': 'Standard Shipping',
                'description': '3-5 business days',
                'cost': shipping_cost,
                'is_free': is_free_shipping,
                'is_selected': not is_free_shipping
            }
            available_shipping_rates.append(standard_shipping)
            
            # Always include free shipping option (which may be disabled)
            free_shipping = {
                'id': 'free',
                'name': 'Free Shipping',
                'description': '5-7 business days',
                'cost': 0,
                'is_free': True,
                'is_selected': is_free_shipping,
                'is_disabled': not is_free_shipping
            }
            available_shipping_rates.append(free_shipping)
            
            # If location-based shipping is enabled, get applicable rates
            if config.enable_location_based_shipping and shipping_address:
                # Logic for location-based rates would go here
                # Similar to the view_cart_view function
                pass
            
            return JsonResponse({
                'success': True,
                'item_total': float(cart_item.total_price),
                'cart_subtotal': float(subtotal),
                'shipping_cost': float(shipping_cost) if not is_free_shipping else 0,
                'is_free_shipping': is_free_shipping,
                'cart_total': float(subtotal + shipping_cost),
                'remaining_for_free': float(remaining_for_free),
                'free_shipping_threshold': float(config.free_shipping_min_amount),
                'shipping_rates': available_shipping_rates
            })
            
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found'})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def wishlist_view(request):
    """View for showing wishlist items"""
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    """View for adding product to wishlist"""
    # Check if user is logged in
    login_check = check_user_login(request, 'add to wishlist', product_id)
    if login_check:
        return login_check
    
    product = get_object_or_404(Product, id=product_id)
    
    # Check if already in wishlist
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    
    if created:
        messages.success(request, f"{product.name} added to your wishlist.")
    else:
        messages.info(request, f"{product.name} is already in your wishlist.")
    
    # Check if request is AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
        
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def remove_from_wishlist(request, wishlist_item_id):
    """View for removing item from wishlist"""
    wishlist_item = get_object_or_404(Wishlist, id=wishlist_item_id, user=request.user)
    product_name = wishlist_item.product.name
    wishlist_item.delete()
    
    messages.success(request, f"{product_name} removed from your wishlist.")
    
    # Check if request is AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
        
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))

def category_view(request, category_slug):
    """View for showing products in a category"""
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category)
    
    # Prepare context with has_image flag for template
    context = {
        'category': category,
        'products': products,
        'has_image': category.image and hasattr(category.image, 'url')
    }
    
    return render(request, 'store/category.html', context)

def search_view(request):
    """View for search results"""
    query = request.GET.get('q', '')
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    else:
        # Show all products when no query is provided
        products = Product.objects.all().order_by('-created_at')
    
    return render(request, 'store/search_results.html', {
        'query': query,
        'products': products
    })

@login_required
def order_detail_view(request, order_id):
    """View for showing order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
    return render(request, 'store/order_detail.html', {
        'order': order,
        'order_items': order_items
    })

# Context processor for global template variables
def global_context(request):
    """Context processor to add global variables to all templates"""
    return {
        'categories': Category.objects.all(),
        'featured_categories': Category.objects.filter(is_featured=True),
        'brands': Brand.objects.all(),
    }

def about_view(request):
    """View for the about page"""
    return render(request, 'store/about.html')

def contact_view(request):
    """View for the contact page"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        # For debugging
        print(f"Received contact form: {name}, {email}, {subject}")
        
        # Save the message to database
        message = Message(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message_text,
            status='unread'  # Ensure status is explicitly set
        )
        
        # If user is logged in, associate message with user
        if request.user.is_authenticated:
            message.user = request.user
            
        message.save()
        
        # For debugging
        print(f"Message saved with ID: {message.id}")
        
        messages.success(request, "Your message has been sent successfully! We'll get back to you soon.")
        return redirect('contact')
        
    return render(request, 'store/contact.html')

@login_required
def my_messages_view(request):
    """View for users to see their own messages"""
    user_messages = Message.objects.filter(user=request.user)
    return render(request, 'store/my_messages.html', {'user_messages': user_messages})

@login_required
def delete_message_view(request, message_id):
    """View for users to delete their own message"""
    message = get_object_or_404(Message, id=message_id, user=request.user)
    
    if request.method == 'POST':
        message.delete()
        messages.success(request, "Your message has been deleted successfully.")
        return redirect('my_messages')
    
    return render(request, 'store/confirm_delete_message.html', {'message': message})

@staff_member_required(login_url='login')
def admin_messages_view(request):
    """Admin view for managing user messages"""
    # Double-check that user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get status filter
    status_filter = request.GET.get('status', '')
    
    # For debugging
    all_messages_count = Message.objects.all().count()
    print(f"Total messages in database: {all_messages_count}")
    
    # Filter messages based on status
    if status_filter and status_filter != 'all':
        user_messages = Message.objects.filter(status=status_filter).order_by('-created_at')
    else:
        user_messages = Message.objects.all().order_by('-created_at')
    
    # For debugging
    print(f"Filtered messages count: {user_messages.count()}")
    
    # Paginate messages
    paginator = Paginator(user_messages, 20)  # 20 messages per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'store/admin_messages.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'total_messages': Message.objects.all().count(),
        'unread_count': Message.objects.filter(status='unread').count(),
    })

@staff_member_required(login_url='login')
def update_message_status_view(request, message_id):
    """Admin view for updating message status"""
    message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '').strip()
        
        # If admin added notes and it's not empty, automatically set status to 'replied'
        if admin_notes and admin_notes != message.admin_notes:
            status = 'replied'
        
        message.status = status
        message.admin_notes = admin_notes
        message.save()
        
        messages.success(request, f"Message status updated to {status}.")
        
        # Check if this is an AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
            
        return redirect('admin_messages')
    
    return render(request, 'store/update_message_status.html', {'message': message})

@staff_member_required(login_url='login')
def admin_shipping_config_view(request):
    """Admin view for configuring shipping settings"""
    # Get or create shipping configuration
    config, created = ShippingConfig.objects.get_or_create(
        pk=1, 
        defaults={
            'enable_free_shipping': False,
            'free_shipping_min_amount': 500.00,
            'default_shipping_cost': 50.00,
            'enable_location_based_shipping': False
        }
    )
    
    if request.method == 'POST':
        # Update shipping configuration
        config.enable_free_shipping = request.POST.get('enable_free_shipping') == 'on'
        config.free_shipping_min_amount = request.POST.get('free_shipping_min')
        config.default_shipping_cost = request.POST.get('default_shipping_cost')
        config.enable_location_based_shipping = request.POST.get('enable_location_based') == 'on'
        config.save()
        
        messages.success(request, "Shipping configuration updated successfully.")
        return redirect('admin_shipping_config')
    
    # Get all shipping rates
    shipping_rates = ShippingRate.objects.all()
    active_rates = shipping_rates.filter(is_active=True).count()
    free_rates = shipping_rates.filter(is_free=True).count()
    
    context = {
        'config': config,
        'rates': shipping_rates,
        'active_rates': active_rates,
        'free_rates': free_rates
    }
    
    return render(request, 'store/admin_shipping_config.html', context)

@staff_member_required(login_url='login')
def manage_shipping_rate_view(request, rate_id=None):
    """View for adding or editing shipping rates"""
    # Check if editing or creating
    if rate_id:
        rate = get_object_or_404(ShippingRate, id=rate_id)
        edit_mode = True
    else:
        rate = None
        edit_mode = False
    
    if request.method == 'POST':
        rate_name = request.POST.get('name')
        rate_type = request.POST.get('rate_type')
        is_active = request.POST.get('is_active') == 'on'
        is_free = request.POST.get('is_free') == 'on'
        cost = request.POST.get('cost')
        min_order_amount = request.POST.get('min_order_amount', 0)
        
        # Process location data based on rate type
        if rate_type == 'nationwide':
            country = 'INDIA'
            region = None
            city = None
            pincode = None
            pincode_from = None
            pincode_to = None
        elif rate_type == 'pincode_range':
            country = 'INDIA'
            region = None
            city = None
            pincode = None
            pincode_from = request.POST.get('pincode_from')
            pincode_to = request.POST.get('pincode_to')
        elif rate_type == 'state':
            country = 'INDIA'
            region = request.POST.get('state')
            city = None
            pincode = None
            pincode_from = None
            pincode_to = None
        elif rate_type == 'city':
            country = 'INDIA'
            region = request.POST.get('state')
            city = request.POST.get('city')
            pincode = None
            pincode_from = None
            pincode_to = None
        else:
            # Default global rate
            country = None
            region = None
            city = None
            pincode = None
            pincode_from = None
            pincode_to = None
        
        if edit_mode:
            # Update existing rate
            rate.name = rate_name
            rate.rate_type = rate_type
            rate.country = country
            rate.region = region
            rate.city = city
            rate.pincode = pincode
            rate.pincode_from = pincode_from
            rate.pincode_to = pincode_to
            rate.cost = cost
            rate.min_order_amount = min_order_amount
            rate.is_active = is_active
            rate.is_free = is_free
            rate.save()
            messages.success(request, "Shipping rate updated successfully.")
        else:
            # Create new rate
            ShippingRate.objects.create(
                name=rate_name,
                rate_type=rate_type,
                country=country,
                region=region,
                city=city,
                pincode=pincode,
                pincode_from=pincode_from,
                pincode_to=pincode_to,
                cost=cost,
                min_order_amount=min_order_amount,
                is_active=is_active,
                is_free=is_free
            )
            messages.success(request, "Shipping rate added successfully.")
        
        return redirect('admin_shipping_config')
    
    context = {
        'rate': rate,
        'edit_mode': edit_mode
    }
    
    return render(request, 'store/manage_shipping_rate.html', context)

@staff_member_required(login_url='login')
def delete_shipping_rate_view(request, rate_id):
    """Admin view for deleting shipping rates"""
    rate = get_object_or_404(ShippingRate, id=rate_id)
    
    if request.method == 'POST':
        name = rate.name
        rate.delete()
        
        messages.success(request, f"Shipping rate '{name}' deleted successfully.")
        return redirect('admin_shipping_config')
    
    return render(request, 'store/confirm_delete_shipping_rate.html', {'rate': rate})

# Shipping Configuration Views
@login_required
@staff_member_required
def shipping_config_view(request):
    """View for managing global shipping configurations"""
    # Get or create default config
    config, created = ShippingConfig.objects.get_or_create(
        pk=1, 
        defaults={
            'enable_free_shipping': False,
            'free_shipping_min_amount': 100.00,
            'default_shipping_cost': 10.00,
            'enable_location_based_shipping': False
        }
    )
    
    if request.method == 'POST':
        form = ShippingConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Shipping configuration updated successfully.")
            return redirect('shipping_config')
    else:
        form = ShippingConfigForm(instance=config)
    
    # Get all shipping rates
    shipping_rates = ShippingRate.objects.filter(is_active=True).order_by('priority', 'name')
    
    context = {
        'form': form,
        'shipping_rates': shipping_rates,
        'section': 'shipping'
    }
    
    return render(request, 'store/admin_shipping.html', context)

@login_required
@staff_member_required
def shipping_rate_add_view(request):
    """View for adding a new shipping rate"""
    if request.method == 'POST':
        form = ShippingRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Shipping rate added successfully.")
            return redirect('shipping_config')
    else:
        form = ShippingRateForm()
    
    context = {
        'form': form,
        'section': 'shipping',
        'title': 'Add Shipping Rate'
    }
    
    return render(request, 'store/admin_shipping_rate_form.html', context)

@login_required
@staff_member_required
def shipping_rate_edit_view(request, rate_id):
    """View for editing an existing shipping rate"""
    rate = get_object_or_404(ShippingRate, id=rate_id)
    
    if request.method == 'POST':
        form = ShippingRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            messages.success(request, "Shipping rate updated successfully.")
            return redirect('shipping_config')
    else:
        form = ShippingRateForm(instance=rate)
    
    context = {
        'form': form,
        'section': 'shipping',
        'rate': rate,
        'title': 'Edit Shipping Rate'
    }
    
    return render(request, 'store/admin_shipping_rate_form.html', context)

@login_required
@staff_member_required
def shipping_rate_delete_view(request, rate_id):
    """View for deleting a shipping rate"""
    rate = get_object_or_404(ShippingRate, id=rate_id)
    
    if request.method == 'POST':
        rate.delete()
        messages.success(request, "Shipping rate deleted successfully.")
        return redirect('shipping_config')
    
    context = {
        'rate': rate,
        'section': 'shipping'
    }
    
    return render(request, 'store/admin_shipping_rate_delete.html', context)

@login_required
@staff_member_required
def shipping_rate_toggle_view(request, rate_id):
    """View for toggling a shipping rate's active status"""
    rate = get_object_or_404(ShippingRate, id=rate_id)
    
    # Toggle status
    rate.is_active = not rate.is_active
    rate.save()
    
    status = "activated" if rate.is_active else "deactivated"
    messages.success(request, f"Shipping rate '{rate.name}' has been {status}.")
    
    return redirect('shipping_config')

# Function to calculate shipping cost for an order
def calculate_shipping_cost(order=None, user=None, cart_total=None, shipping_address=None):
    """
    Calculate shipping cost based on order details and shipping configuration
    
    Parameters:
    - order: Order object (optional)
    - user: User object (optional, used if order not provided)
    - cart_total: Cart total amount (optional, used if order not provided)
    - shipping_address: Shipping address details (optional, used if order not provided)
    
    Returns:
    - shipping_cost: The calculated shipping cost
    - is_free_shipping: Whether free shipping applies
    """
    # Get shipping configuration
    config, created = ShippingConfig.objects.get_or_create(
        pk=1, 
        defaults={
            'enable_free_shipping': False,
            'free_shipping_min_amount': 500.00,
            'default_shipping_cost': 50.00,
            'enable_location_based_shipping': False
        }
    )
    
    # Extract order details
    if order:
        order_total = order.total_amount
        country = None
        region = order.state
        city = order.city
        pincode = order.pincode
    else:
        order_total = cart_total or 0
        shipping_data = shipping_address or {}
        country = shipping_data.get('country')
        region = shipping_data.get('state')
        city = shipping_data.get('city')
        pincode = shipping_data.get('pincode')
    
    # Check for free shipping based on order total
    if config.enable_free_shipping or order_total >= config.free_shipping_min_amount:
        return 0, True
    
    # Check for location-based shipping rates if enabled
    if config.enable_location_based_shipping:
        # First, try to find a pincode-specific rate
        if pincode:
            # Check for exact pincode match
            pincode_rate = ShippingRate.objects.filter(
                rate_type='pincode',
                pincode=pincode,
                is_active=True
            ).first()
            
            if pincode_rate:
                if pincode_rate.is_free:
                    return 0, True
                return pincode_rate.cost, False
            
            # Check for pincode range match
            pincode_range_rates = ShippingRate.objects.filter(
                rate_type='pincode_range',
                is_active=True
            )
            
            for rate in pincode_range_rates:
                if rate.pincode_from and rate.pincode_to:
                    try:
                        if int(rate.pincode_from) <= int(pincode) <= int(rate.pincode_to):
                            pincode_rates = list(pincode_rates) + [rate]
                    except (ValueError, TypeError):
                        continue
            
            # Add pincode rates to available options
            for rate in pincode_rates:
                rate_option = {
                    'id': f'pincode_{rate.id}',
                    'name': rate.name,
                    'description': f'Special rate for your area',
                    'cost': 0 if rate.is_free else rate.cost,
                    'is_free': rate.is_free,
                    'is_selected': False,
                    'rate_type': 'pincode'
                }
                available_shipping_rates.append(rate_option)
        
        # Get rates based on city
        if city:
            city_rates = ShippingRate.objects.filter(
                rate_type='city',
                city__iexact=city,
                is_active=True
            )
            
            for rate in city_rates:
                rate_option = {
                    'id': f'city_{rate.id}',
                    'name': rate.name,
                    'description': f'Delivery to {shipping_address["city"]}',
                    'cost': 0 if rate.is_free else rate.cost,
                    'is_free': rate.is_free,
                    'is_selected': False,
                    'rate_type': 'city'
                }
                available_shipping_rates.append(rate_option)
        
        # Get rates based on state/region
        if region:
            state_rates = ShippingRate.objects.filter(
                rate_type='state',
                region__iexact=region,
                is_active=True
            )
            
            for rate in state_rates:
                rate_option = {
                    'id': f'region_{rate.id}',
                    'name': rate.name,
                    'description': f'Delivery in {shipping_address["state"]}',
                    'cost': 0 if rate.is_free else rate.cost,
                    'is_free': rate.is_free,
                    'is_selected': False,
                    'rate_type': 'region'
                }
                available_shipping_rates.append(rate_option)
        
        # Get nationwide rates
        nationwide_rates = ShippingRate.objects.filter(
            rate_type='nationwide',
            is_active=True
        )
        
        for rate in nationwide_rates:
            rate_option = {
                'id': f'nationwide_{rate.id}',
                'name': rate.name,
                'description': 'All India delivery',
                'cost': 0 if rate.is_free else rate.cost,
                'is_free': rate.is_free,
                'is_selected': False,
                'rate_type': 'nationwide'
            }
            available_shipping_rates.append(rate_option)
    
    # Return default shipping cost if no specific rate applies
    return config.default_shipping_cost, False

@staff_member_required(login_url='login')
def delete_category_view(request, cat_id):
    """Admin view for deleting a category"""
    category = get_object_or_404(Category, id=cat_id)
    
    # Check if category has products
    if category.products.exists():
        messages.error(request, f"Cannot delete category '{category.name}' because it has products. Remove all products from this category first.")
        return redirect('admin_categories')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f"Category '{category_name}' deleted successfully.")
        return redirect('admin_categories')
    
    return render(request, 'store/confirm_delete_category.html', {'category': category})

@login_required
def update_shipping_method(request):
    """AJAX view for updating the selected shipping method"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            method_id = data.get('method_id')
            cost = data.get('cost', 0)
            
            # Store the selected shipping method in the session
            request.session['selected_shipping_method'] = method_id
            request.session['selected_shipping_cost'] = float(cost)
            
            # Get cart total
            cart_items = Cart.objects.filter(user=request.user)
            subtotal = sum(item.total_price for item in cart_items)
            
            # Calculate new total with the selected shipping cost
            total = subtotal + float(cost)
            
            return JsonResponse({
                'success': True,
                'method_id': method_id,
                'shipping_cost': float(cost),
                'cart_total': total
            })
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@staff_member_required(login_url='login')
def admin_reviews_view(request):
    """Admin view for managing product reviews"""
    reviews = Review.objects.all().select_related('user', 'product')
    
    # Filter options
    rating_filter = request.GET.get('rating')
    product_filter = request.GET.get('product')
    user_filter = request.GET.get('user')
    date_filter = request.GET.get('date')
    
    # Apply filters if they exist
    if rating_filter and rating_filter.isdigit():
        reviews = reviews.filter(rating=int(rating_filter))
    
    if product_filter:
        reviews = reviews.filter(product__id=product_filter)
    
    if user_filter:
        reviews = reviews.filter(user__username__icontains=user_filter)
    
    if date_filter:
        # Convert date string to date object
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            reviews = reviews.filter(created_at__date=date_obj)
        except ValueError:
            # Handle invalid date format
            pass
    
    # Delete a review if requested
    if request.method == 'POST' and 'delete_review' in request.POST:
        review_id = request.POST.get('review_id')
        try:
            review = Review.objects.get(id=review_id)
            product_name = review.product.name
            review.delete()
            messages.success(request, f"Review for '{product_name}' has been deleted successfully.")
            return redirect('admin_reviews')
        except Review.DoesNotExist:
            messages.error(request, "Review not found.")
    
    # Get all products and users for filter dropdowns
    all_products = Product.objects.all()
    all_users = User.objects.filter(review__isnull=False).distinct()
    
    # Group reviews by product for statistics
    products_with_reviews = Product.objects.filter(reviews__isnull=False).distinct()
    product_stats = []
    
    for product in products_with_reviews:
        product_reviews = reviews.filter(product=product)
        if product_reviews.exists():
            avg_rating = product_reviews.aggregate(Avg('rating'))['rating__avg']
            total_reviews = product_reviews.count()
            product_stats.append({
                'product': product,
                'avg_rating': avg_rating,
                'total_reviews': total_reviews
            })
    
    # Sort product stats by average rating (highest first)
    product_stats = sorted(product_stats, key=lambda x: x['avg_rating'], reverse=True)
    
    # Calculate rating counts for chart
    rating_counts = []
    for rating in range(1, 6):
        count = Review.objects.filter(rating=rating).count()
        rating_counts.append({
            'rating': rating,
            'count': count
        })
    
    # Paginate the reviews
    paginator = Paginator(reviews, 20)  # Show 20 reviews per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'all_products': all_products,
        'all_users': all_users,
        'product_stats': product_stats,
        'rating_filter': rating_filter,
        'product_filter': product_filter,
        'user_filter': user_filter,
        'date_filter': date_filter,
        'rating_counts': rating_counts
    }
    
    return render(request, 'store/admin_reviews.html', context)
