# accounts/urls.py
from django.urls import path, include
from rest_framework import routers
from .views import RegisterView, LoginView, LogoutView, UserView, ProductViewSet, UserListView, CategoryViewSet, BrandViewSet, MyProductsView, ProductDetailView, PublicUserProfileView, PublicUserProductsView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,  # for obtaining the token pair (access and refresh)
    TokenRefreshView,     # for refreshing the access token
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)  
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    # Use SimpleJWT's built-in token view endpoints:
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user/', UserView.as_view(), name='user'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('myproducts/', MyProductsView.as_view(), name='my-products'),
    path('profile/<str:username>/', PublicUserProfileView.as_view(), name='public-profile'),
    path('profile/<str:username>/products/', PublicUserProductsView.as_view(), name='public-user-products'),
    path('', include(router.urls)),
]