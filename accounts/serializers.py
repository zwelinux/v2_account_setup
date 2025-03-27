# accounts/serializers.py
from rest_framework import serializers
from .models import CustomUser

from .models import Order


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # Include fields you want to expose
        fields = ['id', 'username', 'email', 'profile_picture', 'phone_number', 'country', 'province', 'city', 'last_login']

# Existing RegisterSerializer remains here...
class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 
            'email', 
            'password', 
            'confirm_password', 
            'profile_picture', 
            'phone_number', 
            'country', 
            'province', 
            'city'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords must match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = CustomUser.objects.create_user(
            username=validated_data.get('username'),
            email=validated_data.get('email'),
            password=validated_data.get('password'),
            profile_picture=validated_data.get('profile_picture', None),
            phone_number=validated_data.get('phone_number', None),
            country=validated_data.get('country', None),
            province=validated_data.get('province', None),
            city=validated_data.get('city', None),
        )
        return user

# accounts/serializers.py
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    # seller = serializers.PrimaryKeyRelatedField(read_only=True)
    seller = CustomUserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.title", read_only=True)
    brand_name = serializers.CharField(source="brand.title", read_only=True)  # Assuming 'title' is the field name

    class Meta:
        model = Product
        # fields = '__all__'  # Or list all fields plus "image_url" if you prefer
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
            "category",  # Keep the category ID for reference
            "category_name",  # ✅ New field for category name
            "brand",  # Keep the brand ID for reference
            "brand_name",  # ✅ New field for brand name
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url) 
        return None

from rest_framework import serializers
from .models import Order
from .serializers import ProductSerializer, CustomUserSerializer

class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    buyer = CustomUserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'product',
            'buyer',          # ✅ Add this field
            'quantity',
            'total_price',
            'status',
            'payment_status',
            'created_at',
        ]


from .models import Category, Brand

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'