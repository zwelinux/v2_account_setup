# accounts/serializers.py
from rest_framework import serializers
from .models import CustomUser

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
    seller = serializers.PrimaryKeyRelatedField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'  # Or list all fields plus "image_url" if you prefer

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None



from .models import Category, Brand

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'