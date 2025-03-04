# accounts/views.py
import logging
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging
from rest_framework import generics
from .models import CustomUser
from .serializers import CustomUserSerializer
from .utils import transform_avatar_api, download_image
import os
from django.conf import settings

logger = logging.getLogger(__name__)

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

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        logger.info(f"Login attempt for username: {username}")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)  # Django updates last_login automatically here.
            logger.info("Authentication successful for username: %s", username)
            return Response({"message": "Logged in successfully"}, status=status.HTTP_200_OK)
        logger.info("Authentication failed for username: %s", username)
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

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
            "last_login": user.last_login,  # This is automatically updated by Django's login()
        }, status=status.HTTP_200_OK)
