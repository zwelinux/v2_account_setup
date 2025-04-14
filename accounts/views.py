import logging
import os
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    RegisterSerializer,
    CustomUserSerializer,
    ProductSerializer,
    CategorySerializer,
    BrandSerializer,
    OrderSerializer
)
from .models import CustomUser, Product, Category, Brand, Order, PasswordResetToken
from .utils import transform_avatar_api, download_image
from .authentication import CsrfExemptSessionAuthentication
from .pagination import ProductPagination

# Initialize Logger
logger = logging.getLogger(__name__)

class MyOrderHistoryView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).order_by('-created_at')

class PublicUserProfileView(RetrieveAPIView):
    """Fetches a public user profile by username."""
    permission_classes = [AllowAny]
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    lookup_field = "username"

    def get(self, request, username):
        try:
            user = self.get_queryset().get(username=username)
            serializer = self.get_serializer(user, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            logger.warning(f"User profile not found: {username}")
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PublicUserProductsView(ListAPIView):
    """Fetches all products uploaded by a user (publicly visible)."""
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        username = self.kwargs.get("username")
        return Product.objects.filter(seller__username=username)

    def list(self, request, *args, **kwargs):
        """Custom list method to handle empty product cases."""
        username = self.kwargs.get("username")
        queryset = self.get_queryset()

        if not queryset.exists():
            logger.info(f"No products found for user: {username}")
            return Response({"message": "No products found."}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# List all users endpoint
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

# views.py (only the relevant part is shown)
# views.py
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='User email (required if phone_number is not provided)'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Password confirmation'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number with country code (e.g., +95123456789) (required if email is not provided)'),
                'country': openapi.Schema(type=openapi.TYPE_STRING),
                'province': openapi.Schema(type=openapi.TYPE_STRING),
                'city': openapi.Schema(type=openapi.TYPE_STRING),
                'weight_kg': openapi.Schema(type=openapi.TYPE_NUMBER, description='Weight in kg (optional)'),
                'height_cm': openapi.Schema(type=openapi.TYPE_NUMBER, description='Height in cm (optional)'),
                'chest_bust': openapi.Schema(type=openapi.TYPE_NUMBER, description='Chest/Bust in cm (optional)'),
                'waist': openapi.Schema(type=openapi.TYPE_NUMBER, description='Waist in cm (optional)'),
                'hip': openapi.Schema(type=openapi.TYPE_NUMBER, description='Hip in cm (optional)'),
                'inseam': openapi.Schema(type=openapi.TYPE_NUMBER, description='Inseam in cm (optional)'),
                'foot_size_us': openapi.Schema(type=openapi.TYPE_NUMBER, description='Foot size in US (optional)'),
                'postal_code': openapi.Schema(type=openapi.TYPE_STRING, description='Postal code (required)'),
                'full_address': openapi.Schema(type=openapi.TYPE_STRING, description='Full address (optional)'),
            },
            required=['username', 'password', 'confirm_password', 'postal_code'],  # Removed email and phone_number from required
            example={
                'username': 'john_doe',
                'email': 'john@example.com',
                'password': 'your_password_here',
                'confirm_password': 'your_password_here',
                'phone_number': '+95123456789',
                'country': 'Myanmar',
                'province': 'Yangon',
                'city': 'Yangon',
                'postal_code': '11181',
                'full_address': '123 Main Street, Apt 4B',
                'weight_kg': 70.5,
                'height_cm': 170.0,
            }
        ),
        responses={
            201: openapi.Response("User created successfully"),
            400: openapi.Response("Validation error")
        }
    )
    def post(self, request):
        logger.info("Received registration data: %s", request.data)
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            return Response({
                "message": "User created successfully",
                "access": access_token,
                "refresh": str(refresh)
            }, status=status.HTTP_201_CREATED)

        logger.error("Registration failed: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login using either email or phone number along with password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='User email (optional)'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='User phone number with country code (e.g., +95123456789) (optional)'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='User password'),
            },
            required=['password'],
            example={
                'phone_number': '+95123456789',
                'password': 'your_password_here'
            }
        ),
        responses={
            200: openapi.Response("Login successful"),
            400: openapi.Response("Missing credentials"),
            401: openapi.Response("Invalid credentials")
        }
    )
    def post(self, request):
        identifier = request.data.get('email') or request.data.get('phone_number')
        password = request.data.get('password')
        logger.info(f"Login attempt with identifier: {identifier}")

        if not identifier or not password:
            return Response(
                {"error": "Email or phone number and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate phone number format if provided
        if request.data.get('phone_number') and not identifier.startswith('+'):
            return Response(
                {"error": "Phone number must include country code (e.g., +95123456789)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate using the custom backend
        user = authenticate(request, username=identifier, password=password)

        if user is not None:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": user.phone_number
                }
            }, status=status.HTTP_200_OK)
        return Response(
            {"error": "Invalid email/phone number or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

# ... (rest of views.py remains unchanged)

class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login using either email or phone number along with password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='User email (optional)'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='User phone number with country code (e.g., +12025550123) (optional)'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='User password'),
            },
            required=['password'],
            example={
                'phone_number': '+12025550123',
                'password': 'your_password_here'
            }
        ),
        responses={
            200: openapi.Response("Login successful"),
            400: openapi.Response("Missing credentials"),
            401: openapi.Response("Invalid credentials")
        }
    )
    def post(self, request):
        identifier = request.data.get('email') or request.data.get('phone_number')
        password = request.data.get('password')
        logger.info(f"Login attempt with identifier: {identifier}")

        if not identifier or not password:
            return Response(
                {"error": "Email or phone number and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate phone number format if provided
        if request.data.get('phone_number') and not identifier.startswith('+'):
            return Response(
                {"error": "Phone number must include country code (e.g., +12025550123)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate using the custom backend
        user = authenticate(request, username=identifier, password=password)

        if user is not None:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": user.phone_number
                }
            }, status=status.HTTP_200_OK)
        return Response(
            {"error": "Invalid email/phone number or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        logout(request)
        logger.info("User logged out successfully.")
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
            "country": user.country,
            "province": user.province,
            "city": user.city,
            "last_login": user.last_login,
        }, status=200)
    
    def put(self, request):
        user = request.user
        data = request.data
        user.country = data.get('country', user.country)
        user.province = data.get('province', user.province)
        user.city = data.get('city', user.city)
        user.save()
        return Response({"message": "Shipping address updated successfully."}, status=200)

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.all()
        request = self.request

        keyword = request.query_params.get('keyword')
        price_range = request.query_params.get('price_range')
        sort_by = request.query_params.get('sort_by', 'date-desc')
        category = request.query_params.get('category')
        brand = request.query_params.get('brand')

        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(brand__title__icontains=keyword) |
                Q(category__title__icontains=keyword)
            )

        if price_range:
            try:
                min_price, max_price = map(float, price_range.split("_"))
                queryset = queryset.filter(
                    second_hand_price__gte=min_price,
                    second_hand_price__lte=max_price
                )
            except ValueError:
                pass

        if category and category.isdigit():
            queryset = queryset.filter(category__id=category)

        if brand and brand.isdigit():
            queryset = queryset.filter(brand__id=brand)

        sort_map = {
            "a_z": "title",
            "z_a": "-title",
            "low_to_high": "second_hand_price",
            "high_to_low": "-second_hand_price",
            "date-acs": "created_at",
            "date-desc": "-created_at",
        }
        queryset = queryset.order_by(sort_map.get(sort_by, "-created_at"))

        return queryset

    def get_serializer_context(self):
        return {"request": self.request}

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.seller != request.user:
            return Response(
                {"error": "You are not allowed to edit this product."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.seller != request.user:
            return Response(
                {"error": "You are not allowed to delete this product."},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response({"message": "Product deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("sort_by", openapi.IN_QUERY, description="Sorting options", type=openapi.TYPE_STRING),
            openapi.Parameter("keyword", openapi.IN_QUERY, description="Search by product, brand, or category", type=openapi.TYPE_STRING),
            openapi.Parameter("price_range", openapi.IN_QUERY, description="Price range: min_max (e.g., 100_500)", type=openapi.TYPE_STRING),
            openapi.Parameter("category", openapi.IN_QUERY, description="Filter by category ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("brand", openapi.IN_QUERY, description="Filter by brand ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("limit", openapi.IN_QUERY, description="Results per page", type=openapi.TYPE_INTEGER),
            openapi.Parameter("page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context=self.get_serializer_context())
        return Response(serializer.data)

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'

@method_decorator(csrf_exempt, name='dispatch')
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

@method_decorator(csrf_exempt, name='dispatch')
class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class MyProductsView(ListAPIView):
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user).order_by('-created_at')

class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        orders_data = request.data.get("orders", [])
        if not orders_data:
            return Response({"error": "No orders provided"}, status=400)

        created_orders = []
        for item in orders_data:
            try:
                product = Product.objects.get(id=item.get("product"))
                order = Order.objects.create(
                    buyer=request.user,
                    product=product,
                    quantity=item.get("quantity", 1),
                    total_price=product.second_hand_price * item.get("quantity", 1),
                )
                created_orders.append(OrderSerializer(order).data)
            except Product.DoesNotExist:
                return Response({"error": f"Product with ID {item.get('product')} not found"}, status=404)

        return Response({"message": "Order(s) placed successfully", "orders": created_orders})

class OrderPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
            if order.payment_status == 'Paid':
                return Response({"message": "Order already paid."}, status=400)
            order.payment_status = 'Paid'
            order.save()
            return Response({"message": "Payment successful."})
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)

class SellerOrderView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        return Order.objects.filter(product__seller=self.request.user).order_by('-created_at')

class UpdateOrderStatusView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request, order_id):
        status_value = request.data.get("status")
        if status_value not in ['Pending', 'Shipped', 'Delivered']:
            return Response({"error": "Invalid status"}, status=400)

        try:
            order = Order.objects.get(id=order_id, product__seller=request.user)
            order.status = status_value
            order.save()
            return Response({"message": "Order status updated successfully."})
        except Order.DoesNotExist:
            return Response({"error": "Order not found or you're not the seller."}, status=404)

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Send a password reset link to the user's email address",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'email': openapi.Schema(type=openapi.TYPE_STRING, description='Registered email address')},
            required=['email'],
            example={ 'email': 'user@example.com' }
        ),
        responses={
            200: openapi.Response("Reset link sent"),
            400: openapi.Response("Email required"),
            404: openapi.Response("User not found")
        }
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
            token = get_random_string(length=32)
            PasswordResetToken.objects.filter(user=user).delete()  # Clear old tokens
            reset_token = PasswordResetToken(user=user, token=token)
            reset_token.save()

            reset_url = f"https://ladyfirst.me/reset-password/{token}/"
            
            send_mail(
                "Password Reset Request",
                f"Click to reset your password: {reset_url}\nValid for 1 hour.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"Password reset link sent to {email}")
            return Response({"message": "Reset link sent to your email"}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            logger.warning(f"Reset requested for non-existent email: {email}")
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error sending reset email: {str(e)}")
            return Response({"error": "Failed to send reset email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Reset user's password using a valid token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='New password'),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Confirm new password'),
            },
            required=['new_password', 'confirm_password'],
            example={
                'new_password': 'new_secure_password',
                'confirm_password': 'new_secure_password'
            }
        ),
        responses={
            200: openapi.Response("Password reset successfully"),
            400: openapi.Response("Invalid input"),
            404: openapi.Response("Invalid or expired token")
        }
    )
    def post(self, request, token):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([new_password, confirm_password]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            if not reset_token.is_valid():
                reset_token.delete()
                return Response({"error": "Token has expired"}, status=status.HTTP_404_NOT_FOUND)

            user = reset_token.user
            user.set_password(new_password)
            user.save()
            reset_token.delete()
            logger.info(f"Password reset for {user.email}")
            return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)
        except PasswordResetToken.DoesNotExist:
            logger.warning(f"Invalid reset token: {token}")
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_404_NOT_FOUND)