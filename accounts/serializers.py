from rest_framework import serializers
from .models import CustomUser, Product, Order, Category, Brand
from django.utils.text import slugify

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'profile_picture', 'phone_number', 'country',
            'province', 'city', 'last_login', 'weight_kg', 'height_cm', 'chest_bust',
            'waist', 'hip', 'inseam', 'foot_size_us', 'postal_code', 'full_address'  # Added full_address
        ]

# serializers.py
# accounts/serializers.py
import re
from rest_framework import serializers
from django.db.models import Q
from .models import CustomUser

# accounts/serializers.py
import re
from rest_framework import serializers
from django.db.models import Q
from django.db import IntegrityError
from .models import CustomUser

class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'confirm_password', 'profile_picture',
            'phone_number', 'country', 'province', 'city', 'weight_kg', 'height_cm',
            'chest_bust', 'waist', 'hip', 'inseam', 'foot_size_us', 'postal_code',
            'full_address'
        ]

    def validate(self, data):
        # Ensure at least one of email or phone_number is provided
        if not data.get('email') and not data.get('phone_number'):
            raise serializers.ValidationError("Either email or phone number must be provided.")

        # Validate password match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords must match.")

        # Validate postal_code
        if not data.get('postal_code'):
            raise serializers.ValidationError("Postal code is required.")

        # Handle phone_number: convert empty string to None and validate
        phone_number = data.get('phone_number')
        if phone_number == '':
            data['phone_number'] = None
        elif phone_number:
            # Check phone number format
            if not phone_number.startswith('+'):
                raise serializers.ValidationError("Phone number must include a country code (e.g., +95123456789).")
            if len(phone_number) < 8:
                raise serializers.ValidationError("Phone number is too short.")
            # Check for duplicate phone number
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                raise serializers.ValidationError("This phone number is already in use.")

        # Handle email: convert empty string to None and validate
        email = data.get('email')
        if email == '':
            data['email'] = None
        elif email:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                raise serializers.ValidationError("Invalid email format.")
            # Check for duplicate email
            if CustomUser.objects.filter(email=email).exists():
                raise serializers.ValidationError("This email is already in use.")

        # Convert empty strings to None for optional FloatFields
        float_fields = ['weight_kg', 'height_cm', 'chest_bust', 'waist', 'hip', 'inseam', 'foot_size_us']
        for field in float_fields:
            if field in data and data[field] == '':
                data[field] = None
            elif field in data and data[field] is not None:
                try:
                    data[field] = float(data[field])
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"{field} must be a valid number.")

        if 'full_address' in data and data['full_address'] == '':
            data['full_address'] = None

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        try:
            user = CustomUser.objects.create(**validated_data)
            user.set_password(validated_data['password'])
            user.save()
            return user
        except IntegrityError as e:
            # Catch any IntegrityError (e.g., duplicate phone_number or email)
            if 'phone_number' in str(e):
                raise serializers.ValidationError({"phone_number": "This phone number is already in use."})
            elif 'email' in str(e):
                raise serializers.ValidationError({"email": "This email is already in use."})
            else:
                raise serializers.ValidationError("An error occurred while creating the user.")

class ProductSerializer(serializers.ModelSerializer):
    seller = CustomUserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.title", read_only=True)
    brand_name = serializers.CharField(source="brand.title", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "seller",
            "image_url",
            "title",
            "product_slug",
            "description",
            "original_price",
            "second_hand_price",
            "size",
            "condition",
            "color",
            "authenticity_document",
            "image",
            "created_at",
            "category",
            "category_name",
            "brand",
            "brand_name",
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url) 
        return None

class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    buyer = CustomUserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'product',
            'buyer',
            'quantity',
            'total_price',
            'status',
            'payment_status',
            'created_at',
        ]

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'