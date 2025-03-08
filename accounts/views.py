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



logger = logging.getLogger(__name__)

from rest_framework.permissions import AllowAny
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
import logging
from .models import CustomUser, Product
from .serializers import CustomUserSerializer, ProductSerializer

# Initialize Logger
logger = logging.getLogger(__name__)

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


# class PublicUserProfileView(APIView):
#     permission_classes = [AllowAny]

#     def get(self, request, username):
#         try:
#             user = CustomUser.objects.get(username=username)
#             serializer = CustomUserSerializer(user, context={'request': request})
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except CustomUser.DoesNotExist:
#             return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
# class PublicUserProductsView(generics.ListAPIView):
#     serializer_class = ProductSerializer
#     def get_queryset(self):
#         username = self.kwargs.get("username")
#         return Product.objects.filter(seller__username=username)

# List all users endpoint
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user = serializer.instance
            logger.info("User registered successfully in DB for username: %s", user.username)
            
            # Process profile picture if uploaded
            if 'profile_picture' in request.FILES:
                try:
                    original_path = user.profile_picture.path
                    logger.info("Original profile picture path: %s", original_path)
                    
                    # Transform the image via external API
                    avatar_url = transform_avatar_api(original_path)
                    logger.info("Received avatar URL: %s", avatar_url)
                    
                    if avatar_url:
                        base, ext = os.path.splitext(os.path.basename(original_path))
                        transformed_filename = f"avatar_{base}{ext}"
                        transformed_path = os.path.join(settings.MEDIA_ROOT, transformed_filename)
                        logger.info("Transformed image will be saved as: %s", transformed_path)
                        
                        # Download the transformed image
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
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        logger.error("Registration failed: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    authentication_classes = []  
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        logger.info("Login attempt for username: %s", username)
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info("Login successful for username: %s", username)
            return Response({"message": "Logged in successfully"}, status=status.HTTP_200_OK)
        logger.info("Authentication failed for username: %s", username)
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# @method_decorator(csrf_exempt, name='dispatch')
# class LoginView(APIView):
#     def post(self, request):
#         username = request.data.get('username')
#         password = request.data.get('password')
#         logger.info("Login attempt for username: %s", username)
#         user = authenticate(username=username, password=password)
#         if user is not None:
#             login(request, user)  # Django updates last_login automatically here.
#             logger.info("Authentication successful for username: %s", username)
#             return Response({"message": "Logged in successfully"}, status=status.HTTP_200_OK)
#         logger.info("Authentication failed for username: %s", username)
#         return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

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
    permission_classes = [IsAuthenticated]  # Only accessible if logged in.
    
    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "email": user.email,
            "last_login": user.last_login,
        }, status=status.HTTP_200_OK)



@method_decorator(csrf_exempt, name='dispatch')
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.order_by('-created_at')
    serializer_class = ProductSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)  # Ensure authentication is enabled
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        seller_id = str(instance.seller.pk)
        user_id = str(request.user.pk)
        logger.info("Attempting to delete product %s. Seller ID: %s, Request user ID: %s",
                    instance.pk, seller_id, user_id)
        if seller_id != user_id:
            logger.warning("Deletion forbidden: user %s is not the owner of product %s", user_id, instance.pk)
            return Response(
                {"error": "You are not allowed to delete this product."},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        logger.info("Product %s deleted successfully.", instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Ensure the user is the owner
        if instance.seller != request.user:
            return Response({"error": "You are not allowed to edit this product."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=True)  # Allow partial updates
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



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

class MyProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user).order_by('-created_at')
