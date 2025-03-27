import logging
import os
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from .serializers import (
    RegisterSerializer,
    CustomUserSerializer,
    ProductSerializer,
    CategorySerializer,
    BrandSerializer
)
from .models import CustomUser, Product, Category, Brand
from .utils import transform_avatar_api, download_image
from .authentication import CsrfExemptSessionAuthentication
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny

from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework import status
import logging

from .models import CustomUser, Product
from .serializers import CustomUserSerializer, ProductSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer
import logging
import os
from django.conf import settings
from .utils import transform_avatar_api, download_image
from rest_framework_simplejwt.authentication import JWTAuthentication

from .pagination import ProductPagination
from django.db.models import Q

from .models import Order
from .serializers import OrderSerializer

from .models import Order
from .serializers import OrderSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from django.db.models import Q
from .pagination import ProductPagination  # ✅ Make sure you’ve created the custom pagination class

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q

from rest_framework.decorators import action
from rest_framework import permissions


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
    permission_classes = [AllowAny]  #

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

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]  # ✅ Allow unauthenticated users

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            logger.info("User registered successfully in DB for username: %s", user.username)

            # ✅ Generate JWT tokens for the user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            # ✅ Process profile picture if uploaded
            if 'profile_picture' in request.FILES:
                try:
                    original_path = user.profile_picture.path
                    logger.info("Original profile picture path: %s", original_path)

                    # ✅ Transform the image via external API
                    avatar_url = transform_avatar_api(original_path)
                    logger.info("Received avatar URL: %s", avatar_url)

                    if avatar_url:
                        base, ext = os.path.splitext(os.path.basename(original_path))
                        transformed_filename = f"avatar_{base}{ext}"
                        transformed_path = os.path.join(settings.MEDIA_ROOT, transformed_filename)
                        logger.info("Transformed image will be saved as: %s", transformed_path)

                        # ✅ Download the transformed image
                        if download_image(avatar_url, transformed_path):
                            user.profile_picture = transformed_filename
                            user.save()
                            logger.info("User profile picture updated to cartoon avatar: %s", transformed_filename)
                        else:
                            logger.error("Failed to download the transformed image.")
                    else:
                        logger.error("No avatar URL returned from the transformation API.")
                except Exception as e:
                    logger.error("Avatar transformation exception: %s", e)

            # ✅ Return user info along with JWT tokens
            return Response({
                "message": "User created successfully",
                "access": access_token,  # ✅ Send access token
                "refresh": str(refresh)  # ✅ Send refresh token
            }, status=status.HTTP_201_CREATED)

        logger.error("Registration failed: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    Login users using EMAIL and password instead of username.
    """

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = User.objects.get(email=email)  # ✅ Find user by email
        except User.DoesNotExist:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response({
            "access": access_token,
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    # Disable authentication for this endpoint to bypass CSRF checks
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        logout(request)
        logger.info("User logged out successfully.")
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class UserView(APIView):
    permission_classes = [IsAuthenticated]  # ✅ Requires authentication

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
    """Handles product operations (CRUD) with authentication & permissions."""

    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.all()
        request = self.request

        # ✅ Filters
        keyword = request.query_params.get('keyword')
        price_range = request.query_params.get('price_range')
        sort_by = request.query_params.get('sort_by', 'date-desc')
        category = request.query_params.get('category')  # ✅ Category filter
        brand = request.query_params.get('brand')        # ✅ Brand filter

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

        # ✅ Sorting
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
    authentication_classes = [JWTAuthentication]  # ✅ Ensure JWT is used
    permission_classes = [IsAuthenticated]  # ✅ Only authenticated users can access

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

