import secrets
import logging
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import authenticate
from .serializers import (
    RegisterSerializer, CustomUserSerializer, ProductSerializer, CategorySerializer,
    BrandSerializer, OrderSerializer, OTPSerializer, OTPVerifySerializer, AccountSetupSerializer
)
from .models import CustomUser, Product, Category, Brand, Order, OTPCode, PasswordResetToken
from .pagination import *


logger = logging.getLogger(__name__)

class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Send a one-time password (OTP) to the user's email or phone number for registration.",
        request_body=OTPSerializer,
        responses={
            200: openapi.Response("OTP sent successfully", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="OTP sent successfully")
                }
            )),
            400: "Invalid email or phone number",
            500: "Failed to send OTP"
        }
    )
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')
            identifier = email or phone_number

            otp_code = str(random.randint(100000, 999999))
            otp = OTPCode(
                user=None,  # No user yet
                code=otp_code,
                identifier=identifier
            )
            otp.save()

            try:
                if email:
                    send_mail(
                        "Your OTP Code",
                        f"Your OTP code is {otp_code}. It is valid for 10 minutes.",
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    logger.info(f"OTP sent to email: {email}")
                else:
                    logger.info(f"OTP {otp_code} would be sent to phone: {phone_number}")
                return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                otp.delete()
                logger.error(f"Failed to send OTP for {identifier}: {str(e)}")
                return Response({"error": f"Failed to send OTP: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Verify the OTP and register a new user.",
        request_body=OTPVerifySerializer,
        responses={
            201: openapi.Response("User created successfully", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="User created successfully"),
                    'access': openapi.Schema(type=openapi.TYPE_STRING, example="access_token"),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, example="refresh_token")
                }
            )),
            400: "Invalid OTP or user data",
            404: "OTP not found or expired"
        }
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')
            identifier = email or phone_number
            code = serializer.validated_data['code']
            password = serializer.validated_data['password']
            username = serializer.validated_data['username']

            try:
                otp = OTPCode.objects.get(identifier=identifier, code=code)
                if not otp.is_valid():
                    otp.delete()
                    logger.warning(f"Expired OTP for {identifier}")
                    return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
            except OTPCode.DoesNotExist:
                logger.warning(f"Invalid OTP code for {identifier}")
                return Response({"error": "Invalid OTP code"}, status=status.HTTP_400_BAD_REQUEST)

            # Create user
            user_data = {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'is_active': True
            }
            user = CustomUser.objects.create(**user_data)
            user.set_password(password)
            user.save()

            otp.delete()  # Clean up OTP

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            logger.info(f"User {user.id} created successfully via OTP")
            return Response({
                "message": "User created successfully",
                "access": access_token,
                "refresh": str(refresh)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user (alternative to OTP flow)",
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response("User created successfully"),
            400: openapi.Response("Validation error")
        }
    )
    def post(self, request):
        logger.info("Received registration data")
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            logger.info(f"User {user.id} registered successfully")
            return Response({
                "message": "User created successfully",
                "access": access_token,
                "refresh": str(refresh)
            }, status=status.HTTP_201_CREATED)

        logger.error(f"Registration failed: {serializer.errors}")
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
            401: openapi.Response("Invalid credentials"),
            404: openapi.Response("User not found")
        }
    )
    def post(self, request):
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        logger.info(f"Login attempt with email: {email}, phone_number: {phone_number}")

        if not (email or phone_number) or not password:
            return Response(
                {"error": "Email or phone number and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if phone_number and not phone_number.startswith('+'):
            return Response(
                {"error": "Phone number must include country code (e.g., +95123456789)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Look up user by email or phone_number
        try:
            if email:
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            logger.warning(f"User not found for email: {email}, phone_number: {phone_number}")
            return Response(
                {"error": "Invalid email/phone number or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Authenticate using the user's username
        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user and authenticated_user.is_active:
            refresh = RefreshToken.for_user(authenticated_user)
            logger.info(f"User {authenticated_user.id} logged in successfully")
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": authenticated_user.id,
                    "username": authenticated_user.username,
                    "email": authenticated_user.email,
                    "phone_number": authenticated_user.phone_number,
                    "is_setup_complete": authenticated_user.is_setup_complete
                }
            }, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Invalid password for user: {user.username}")
            return Response(
                {"error": "Invalid email/phone number or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Logout user by blacklisting the refresh token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token to blacklist'),
            },
            required=['refresh'],
            example={
                'refresh': 'your_refresh_token_here'
            }
        ),
        responses={
            200: openapi.Response("Logged out successfully"),
            400: openapi.Response("Invalid input"),
            401: openapi.Response("Unauthorized")
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                logger.warning(f"Logout attempt by user ID {request.user.id if request.user else 'unknown'} with no refresh token")
                return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"User {request.user.id} logged out successfully")
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Logout failed for user ID {request.user.id if request.user else 'unknown'}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AccountSetupView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Complete user account setup after first login",
        request_body=AccountSetupSerializer,
        responses={
            200: openapi.Response("Account setup completed successfully"),
            400: openapi.Response("Validation error")
        }
    )
    def put(self, request):
        user = request.user
        serializer = AccountSetupSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user.is_setup_complete = True
            user.save()
            logger.info(f"Account setup completed for user ID {user.id}")
            return Response({
                "message": "Account setup completed successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "is_setup_complete": user.is_setup_complete
                }
            }, status=status.HTTP_200_OK)
        logger.error(f"Account setup failed for user ID {user.id}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve or update authenticated user's profile",
        responses={
            200: openapi.Response("User profile retrieved or updated successfully")
        }
    )
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
            "is_setup_complete": user.is_setup_complete,
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Update authenticated user's shipping address",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'country': openapi.Schema(type=openapi.TYPE_STRING),
                'province': openapi.Schema(type=openapi.TYPE_STRING),
                'city': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response("Shipping address updated successfully")
        }
    )
    def put(self, request):
        user = request.user
        data = request.data
        user.country = data.get('country', user.country)
        user.province = data.get('province', user.province)
        user.city = data.get('city', user.city)
        user.save()
        logger.info(f"Shipping address updated for user ID {user.id}")
        return Response({"message": "Shipping address updated successfully."}, status=status.HTTP_200_OK)

class MyOrderHistoryView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).order_by('-created_at')

class PublicUserProfileView(RetrieveAPIView):
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
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        username = self.kwargs.get("username")
        return Product.objects.filter(seller__username=username)

    def list(self, request, *args, **kwargs):
        username = self.kwargs.get("username")
        queryset = self.get_queryset()

        if not queryset.exists():
            logger.info(f"No products found for user: {username}")
            return Response({"message": "No products found."}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
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
                logger.warning(f"Invalid price range format: {price_range}")
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
            logger.warning(f"User {request.user.id} attempted to edit product {instance.id} they don't own.")
            return Response(
                {"error": "You are not allowed to edit this product."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Product {instance.id} updated by user {request.user.id}")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.seller != request.user:
            logger.warning(f"User {request.user.id} attempted to delete product {instance.id} they don't own.")
            return Response(
                {"error": "You are not allowed to delete this product."},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        logger.info(f"Product {instance.id} deleted by user {request.user.id}")
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

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

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

    @swagger_auto_schema(
        operation_description="Place an order for one or more products",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'orders': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'product': openapi.Schema(type=openapi.TYPE_INTEGER, description='Product ID'),
                            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity', default=1),
                        }
                    )
                )
            },
            required=['orders'],
            example={
                'orders': [
                    {'product': 1, 'quantity': 2},
                    {'product': 2, 'quantity': 1}
                ]
            }
        ),
        responses={
            200: openapi.Response("Order(s) placed successfully"),
            400: openapi.Response("No orders provided"),
            404: openapi.Response("Product not found")
        }
    )
    def post(self, request):
        orders_data = request.data.get("orders", [])
        if not orders_data:
            return Response({"error": "No orders provided"}, status=status.HTTP_400_BAD_REQUEST)

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
                logger.warning(f"Product with ID {item.get('product')} not found for user {request.user.id}")
                return Response({"error": f"Product with ID {item.get('product')} not found"}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"User {request.user.id} placed order(s): {created_orders}")
        return Response({"message": "Order(s) placed successfully", "orders": created_orders}, status=status.HTTP_200_OK)

class OrderPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Process payment for an order",
        responses={
            200: openapi.Response("Payment successful"),
            400: openapi.Response("Order already paid"),
            404: openapi.Response("Order not found")
        }
    )
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
            if order.payment_status == 'Paid':
                logger.info(f"Order {order_id} already paid by user {request.user.id}")
                return Response({"message": "Order already paid."}, status=status.HTTP_400_BAD_REQUEST)
            order.payment_status = 'Paid'
            order.save()
            logger.info(f"Payment successful for order {order_id} by user {request.user.id}")
            return Response({"message": "Payment successful."}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            logger.warning(f"Order {order_id} not found for user {request.user.id}")
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

class SellerOrderView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        return Order.objects.filter(product__seller=self.request.user).order_by('-created_at')

class UpdateOrderStatusView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Update the status of an order (seller only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Order status (Pending, Shipped, Delivered)'),
            },
            required=['status'],
            example={'status': 'Shipped'}
        ),
        responses={
            200: openapi.Response("Order status updated successfully"),
            400: openapi.Response("Invalid status"),
            404: openapi.Response("Order not found or unauthorized")
        }
    )
    def put(self, request, order_id):
        status_value = request.data.get("status")
        if status_value not in ['Pending', 'Shipped', 'Delivered']:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id, product__seller=request.user)
            order.status = status_value
            order.save()
            logger.info(f"Order {order_id} status updated to {status_value} by seller {request.user.id}")
            return Response({"message": "Order status updated successfully."}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            logger.warning(f"Order {order_id} not found or user {request.user.id} is not the seller")
            return Response({"error": "Order not found or you're not the seller."}, status=status.HTTP_404_NOT_FOUND)

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Send a password reset link to the user's email address or via SMS to their phone number",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Registered email address (optional)'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Registered phone number with country code (e.g., +95123456789) (optional)'),
            },
            required=[],
            example={'email': 'user@example.com'}
        ),
        responses={
            200: openapi.Response("Reset link sent"),
            400: openapi.Response("Email or phone number required"),
            404: openapi.Response("User not found"),
            500: openapi.Response("Failed to send reset email or SMS")
        }
    )
    def post(self, request):
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')

        if not email and not phone_number:
            return Response({"error": "Email or phone number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if email:
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone_number=phone_number)

            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.filter(user=user).delete()
            reset_token = PasswordResetToken(user=user, token=token)
            reset_token.save()

            reset_url = f"https://ladyfirst.me/reset-password/{token}/"

            if email:  # Simulate sending email by logging
                logger.info(f"[DEV] Password reset link would be sent via email to {email} for user ID {user.id}: {reset_url}")
                print(f"[DEV] Password reset link for {email}: {reset_url}")  # Also print to console for easy access
                return Response({"message": "Reset link sent to your email"}, status=status.HTTP_200_OK)
            else:  # Simulate sending SMS by logging
                logger.info(f"[DEV] Password reset link would be sent via SMS to {phone_number} for user ID {user.id}: {reset_url}")
                print(f"[DEV] Password reset link for {phone_number}: {reset_url}")  # Also print to console
                return Response({"message": "Reset link sent via SMS to your phone"}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            identifier = email or phone_number
            logger.warning(f"Reset requested for non-existent identifier: {identifier}")
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating reset link: {str(e)}")
            return Response({"error": "Failed to generate reset link"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                logger.warning(f"Expired reset token: {token}")
                return Response({"error": "Token has expired"}, status=status.HTTP_404_NOT_FOUND)

            user = reset_token.user
            user.set_password(new_password)
            user.save()
            reset_token.delete()
            logger.info(f"Password reset for user ID {user.id}")
            return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)
        except PasswordResetToken.DoesNotExist:
            logger.warning(f"Invalid reset token: {token}")
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_404_NOT_FOUND)