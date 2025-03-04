# accounts/urls.py
from django.urls import path, include
from rest_framework import routers
from .views import RegisterView, LoginView, LogoutView, UserView, ProductViewSet, UserListView, CategoryViewSet, BrandViewSet, MyProductsView, ProductDetailView

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)  
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user/', UserView.as_view(), name='user'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('myproducts/', MyProductsView.as_view(), name='my-products'),
    path('products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),
    path('', include(router.urls)),
]
