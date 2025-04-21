import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saree_site.settings')
django.setup()

from django.contrib.auth.models import User
from store.models import Product, Review
from django.utils import timezone

def create_test_reviews():
    print("Creating test reviews...")
    
    # Get a user and a product
    try:
        users = User.objects.all()
        products = Product.objects.all()
        
        if not users.exists():
            print("No users found. Please create a user first.")
            return
            
        if not products.exists():
            print("No products found. Please create a product first.")
            return
            
        user = users.first()
        for product in products[:3]:  # Take first 3 products
            # Check if a review already exists
            if not Review.objects.filter(user=user, product=product).exists():
                # Create a review
                review = Review(
                    product=product,
                    user=user,
                    rating=5,
                    title=f"Test Review for {product.name}",
                    comment=f"This is a test review for {product.name}. It's a great product!",
                    created_at=timezone.now(),
                    updated_at=timezone.now()
                )
                
                try:
                    review.save()
                    print(f"Created review for {product.name}")
                except Exception as e:
                    print(f"Error creating review: {e}")
            else:
                print(f"Review already exists for {product.name}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_test_reviews() 