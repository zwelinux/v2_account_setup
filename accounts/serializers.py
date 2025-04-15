from rest_framework import serializers
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
import re
import random
from .models import CustomUser, OTPCode, Product, Order, Category, Brand
from django.contrib.auth.password_validation import validate_password

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'profile_picture', 'phone_number', 'country',
            'province', 'city', 'last_login', 'weight_kg', 'height_cm', 'chest_bust',
            'waist', 'hip', 'inseam', 'foot_size_us', 'postal_code', 'full_address'
        ]

class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        if not data.get('email') and not data.get('phone_number'):
            raise serializers.ValidationError("Either email or phone number must be provided.")

        if data.get('phone_number'):
            phone_number = data['phone_number'].replace(" ", "").replace("-", "")
            data['phone_number'] = phone_number
            if not phone_number.startswith('+'):
                raise serializers.ValidationError("Phone number must include a country code (e.g., +95123456789).")
            if len(phone_number) < 8:
                raise serializers.ValidationError("Phone number is too short.")
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                raise serializers.ValidationError("This phone number is already in use.")

        if data.get('email'):
            email = data['email'].lower().strip()
            data['email'] = email
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                raise serializers.ValidationError("Invalid email format.")
            if CustomUser.objects.filter(email=email).exists():
                raise serializers.ValidationError("This email is already in use.")

        return data

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    code = serializers.CharField(max_length=6)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(max_length=150, required=True)

    def validate(self, data):
        if not data.get('email') and not data.get('phone_number'):
            raise serializers.ValidationError("Either email or phone number must be provided.")

        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords must match.")

        # Enforce stronger password policy
        try:
            validate_password(data['password'])
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"password": str(e)})

        if len(data['username']) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")

        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("This username is already taken.")

        return data

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
        if not data.get('email') and not data.get('phone_number'):
            raise serializers.ValidationError("Either email or phone number must be provided.")

        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords must match.")

        try:
            validate_password(data['password'])
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"password": str(e)})

        phone_number = data.get('phone_number')
        if phone_number == '':
            data['phone_number'] = None
        elif phone_number:
            if not phone_number.startswith('+'):
                raise serializers.ValidationError("Phone number must include a country code (e.g., +95123456789).")
            if len(phone_number) < 8:
                raise serializers.ValidationError("Phone number is too short.")
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                raise serializers.ValidationError("This phone number is already in use.")

        email = data.get('email')
        if email == '':
            data['email'] = None
        elif email:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                raise serializers.ValidationError("Invalid email format.")
            if CustomUser.objects.filter(email=email).exists():
                raise serializers.ValidationError("This email is already in use.")

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
        except Exception as e:
            if 'phone_number' in str(e).lower():
                raise serializers.ValidationError({"phone_number": "This phone number is already in use."})
            elif 'email' in str(e).lower():
                raise serializers.ValidationError({"email": "This email is already in use."})
            else:
                raise serializers.ValidationError(f"An error occurred while creating the user: {str(e)}")

class AccountSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'phone_number', 'country', 'province', 'city',
            'postal_code', 'full_address', 'weight_kg', 'height_cm', 'chest_bust',
            'waist', 'hip', 'inseam', 'foot_size_us'
        ]

    def validate(self, data):
        if not data.get('username'):
            raise serializers.ValidationError("Username is required.")
        if CustomUser.objects.filter(username=data['username']).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("This username is already taken.")

        if not data.get('country'):
            raise serializers.ValidationError("Country is required.")
        if not data.get('province'):
            raise serializers.ValidationError("Province is required.")
        if not data.get('city'):
            raise serializers.ValidationError("City is required.")
        if not data.get('postal_code'):
            raise serializers.ValidationError("Postal code is required.")

        # Handle email
        email = data.get('email')
        if email == '':
            data['email'] = None
        if email and email != self.instance.email:
            email = email.lower().strip()
            data['email'] = email
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                raise serializers.ValidationError("Invalid email format.")
            if CustomUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("This email is already in use.")

        # Handle phone_number: preserve existing if not provided
        phone_number = data.get('phone_number')
        if phone_number == '':
            data['phone_number'] = None
        if phone_number and phone_number != self.instance.phone_number:
            phone_number = phone_number.replace(" ", "").replace("-", "")
            data['phone_number'] = phone_number
            if not phone_number.startswith('+'):
                raise serializers.ValidationError("Phone number must include a country code (e.g., +95123456789).")
            if len(phone_number) < 8:
                raise serializers.ValidationError("Phone number is too short.")
            if CustomUser.objects.filter(phone_number=phone_number).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("This phone number is already in use.")
        elif 'phone_number' not in data:
            # Preserve existing phone_number if not provided
            data['phone_number'] = self.instance.phone_number

        # Enforce either email or phone_number must exist
        if not data.get('email') and not data.get('phone_number'):
            raise serializers.ValidationError("Either email or phone number must be provided.")

        float_fields = ['weight_kg', 'height_cm', 'chest_bust', 'waist', 'hip', 'inseam', 'foot_size_us']
        for field in float_fields:
            if field in data and data[field] == '':
                data[field] = None
            elif field in data and data[field] is not None:
                try:
                    value = float(data[field])
                    if value < 0:
                        raise serializers.ValidationError(f"{field} must be a positive number.")
                    data[field] = value
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"{field} must be a valid number.")

        if 'full_address' in data and data['full_address'] == '':
            data['full_address'] = None

        return data

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
        return None if not (obj.image and request) else request.build_absolute_uri(obj.image.url)

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