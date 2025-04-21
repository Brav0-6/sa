# store/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import Product, Category, Brand, UserProfile, Review, ShippingConfig, ShippingRate

# Edit Profile Form
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

# Add Product Form
class ProductForm(forms.ModelForm):
    # Make category a required field with proper choices
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select a category",
        required=True
    )
    
    # Add brand field as optional
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        empty_label="Select a brand (optional)",
        required=False
    )
    
    # Additional fields
    is_featured = forms.BooleanField(required=False, initial=False)
    on_sale = forms.BooleanField(required=False, initial=False)
    sale_price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # Make sure to set a default for stock
    stock = forms.IntegerField(required=True, initial=1, min_value=0)
    
    # Form description field should be a Textarea
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=True
    )
    
    # Rename image field to main_image for consistency
    main_image = forms.ImageField(required=True)
    
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'sale_price', 'category', 'brand', 'stock', 'fabric_type', 'is_featured', 'on_sale', 'main_image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'id': 'product-name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'product-description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'id': 'product-price', 'min': '0'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'id': 'product-sale-price', 'min': '0'}),
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'product-category'}),
            'brand': forms.Select(attrs={'class': 'form-control', 'id': 'product-brand'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'id': 'product-stock', 'min': '0'}),
            'fabric_type': forms.TextInput(attrs={'class': 'form-control', 'id': 'product-fabric-type'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'product-featured'}),
            'on_sale': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'product-on-sale'}),
            'main_image': forms.FileInput(attrs={'class': 'form-control-file', 'id': 'product-image'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Checkboxes need different styling
        self.fields['is_featured'].widget.attrs['class'] = 'form-check-input'
        self.fields['on_sale'].widget.attrs['class'] = 'form-check-input'
        
    def clean(self):
        cleaned_data = super().clean()
        on_sale = cleaned_data.get('on_sale')
        sale_price = cleaned_data.get('sale_price')
        price = cleaned_data.get('price')
        
        # Validate sale price if on_sale is checked
        if on_sale and not sale_price:
            self.add_error('sale_price', 'Sale price is required when product is on sale')
        
        # Make sure sale price is less than regular price
        if sale_price and price and sale_price >= price:
            self.add_error('sale_price', 'Sale price must be less than regular price')
            
        return cleaned_data
        
    def save(self, commit=True):
        instance = super(ProductForm, self).save(commit=False)
        
        # Transfer main_image to the image field in the Product model
        if 'main_image' in self.cleaned_data:
            instance.image = self.cleaned_data['main_image']
            
        if commit:
            instance.save()
            
        return instance

# Review Form
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '5', 'step': '1'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AddProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'brand', 'price', 'sale_price', 'stock', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Product Description', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Regular Price'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sale Price (optional)'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Stock Quantity'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ShippingConfigForm(forms.Form):
    free_shipping_threshold = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Free shipping for orders above this amount (0 to disable)'
        })
    )
    default_shipping_cost = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Default shipping cost'
        })
    )

class ShippingRateForm(forms.ModelForm):
    class Meta:
        model = ShippingRate
        fields = ['name', 'rate_type', 'country', 'region', 'city', 'pincode', 'pincode_from', 'pincode_to', 'cost', 'is_active', 'is_free', 'min_order_amount']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard US Shipping'}),
            'rate_type': forms.Select(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country code (leave empty for global)'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Region/State (leave empty if not applicable)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (if applicable)'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode (if applicable)'}),
            'pincode_from': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Starting pincode for range'}),
            'pincode_to': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ending pincode for range'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'min_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def clean_country(self):
        country = self.cleaned_data.get('country')
        if country:
            return country.upper()
        return country
        
    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country')
        region = cleaned_data.get('region')
        
        # If a region is specified, a country must also be specified
        if region and not country:
            self.add_error('region', 'You must specify a country when adding a region-specific rate')
            
        return cleaned_data
