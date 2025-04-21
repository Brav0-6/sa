// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Product image hover effect
    initializeProductImageZoom();
    
    // Quantity controls in cart
    initializeQuantityControls();
    
    // Add to cart animation
    initializeAddToCartButtons();
    
    // Initialize any carousels
    initializeCarousels();
    
    // Form validation
    initializeFormValidation();
});

// Product image zoom effect on hover
function initializeProductImageZoom() {
    const productImages = document.querySelectorAll('.product-card img, .product-detail-img');
    
    productImages.forEach(img => {
        img.addEventListener('mouseover', function() {
            this.style.transform = 'scale(1.05)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        img.addEventListener('mouseout', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

// Quantity control buttons
function initializeQuantityControls() {
    const decrementButtons = document.querySelectorAll('.decrement-qty');
    const incrementButtons = document.querySelectorAll('.increment-qty');
    
    decrementButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const input = this.nextElementSibling;
            let value = parseInt(input.value);
            if (value > 1) {
                input.value = value - 1;
                updateCartItem(input);
            }
        });
    });
    
    incrementButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const input = this.previousElementSibling;
            let value = parseInt(input.value);
            input.value = value + 1;
            updateCartItem(input);
        });
    });
}

// Update cart when quantity changes
function updateCartItem(input) {
    const itemId = input.getAttribute('data-item-id');
    const quantity = input.value;
    
    // You would normally make an AJAX call to update the cart
    console.log(`Updated item ${itemId} to quantity ${quantity}`);
    
    // Update the subtotal and total if needed
    updateCartTotals();
}

// Calculate and update cart totals
function updateCartTotals() {
    const priceElements = document.querySelectorAll('.item-price');
    const quantityInputs = document.querySelectorAll('.quantity-input');
    let total = 0;
    
    for (let i = 0; i < priceElements.length; i++) {
        const price = parseFloat(priceElements[i].textContent.replace('₹', ''));
        const quantity = parseInt(quantityInputs[i].value);
        total += price * quantity;
    }
    
    const totalElement = document.querySelector('.cart-total');
    if (totalElement) {
        totalElement.textContent = `₹${total.toFixed(2)}`;
    }
}

// Add to cart animation
function initializeAddToCartButtons() {
    const addButtons = document.querySelectorAll('.add-to-cart-btn');
    
    addButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // If it's not a form submit button, prevent default
            if (this.getAttribute('type') !== 'submit') {
                e.preventDefault();
                
                // Get product ID
                const productId = this.getAttribute('data-product-id');
                if (!productId) return;
                
                // Show loading state
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
                this.disabled = true;
                
                // Get CSRF token
                const csrftoken = getCookie('csrftoken');
                
                // Make AJAX request to add to cart
                fetch(`/add-to-cart/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        quantity: 1 // Default quantity
                    })
                })
                .then(response => response.json())
                .then(data => {
                    // Show success message
                    this.classList.add('btn-success');
                    this.innerHTML = '✓ Added';
                    
                    // Update cart count if provided
                    if (data.cart_count !== undefined && typeof updateCartCount === 'function') {
                        updateCartCount(data.cart_count);
                    }
                    
                    // Show toast notification if needed
                    if (typeof showToast === 'function') {
                        showToast('Product added to cart!');
                    }
                    
                    // Reset button after delay
                    setTimeout(() => {
                        this.classList.remove('btn-success');
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }, 2000);
                })
                .catch(error => {
                    console.error('Error adding to cart:', error);
                    this.innerHTML = 'Error';
                    
                    // Reset button after delay
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }, 2000);
                });
            }
        });
    });
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Function to show toast notifications
function showToast(message) {
    // Check if a toast container already exists
    let toast = document.querySelector('.product-toast');
    
    if (!toast) {
        // Create toast container if it doesn't exist
        toast = document.createElement('div');
        toast.className = 'product-toast';
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.backgroundColor = 'rgba(40, 167, 69, 0.9)';
        toast.style.color = 'white';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '4px';
        toast.style.zIndex = '1050';
        toast.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
        toast.style.opacity = '0';
        toast.style.transition = 'all 0.3s ease';
        
        document.body.appendChild(toast);
    }
    
    // Update toast message
    toast.textContent = message;
    toast.style.display = 'block';
    
    // Animation
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 100);
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            toast.style.display = 'none';
        }, 300);
    }, 3000);
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (typeof bootstrap !== 'undefined') {
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
}

// Initialize any carousels
function initializeCarousels() {
    // If using Bootstrap carousel
    if (document.querySelector('.carousel') && typeof bootstrap !== 'undefined') {
        const carouselElement = document.querySelector('.carousel');
        const carousel = new bootstrap.Carousel(carouselElement, {
            interval: 5000,
            wrap: true
        });
    }
}

// Basic form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}
