from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'brands', views.BrandViewSet, basename='brand')

# Authentication URLs
auth_patterns = [
    path('send-otp/', views.SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/<str:token>/', views.ResetPasswordView.as_view(), name='reset_password'),
]

# User-related URLs
user_patterns = [
    path('user/', views.UserView.as_view(), name='user'),
    path('account-setup/', views.AccountSetupView.as_view(), name='account_setup'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('profile/<str:username>/', views.PublicUserProfileView.as_view(), name='public_user_profile'),
    path('user-products/<str:username>/', views.PublicUserProductsView.as_view(), name='public_user_products'),
]

# Product and order-related URLs
product_order_patterns = [
    path('my-products/', views.MyProductsView.as_view(), name='my_products'),
    path('orders/', views.MyOrderHistoryView.as_view(), name='order_history'),
    path('seller/orders/', views.SellerOrderView.as_view(), name='seller_orders'),
    path('place-order/', views.PlaceOrderView.as_view(), name='place_order'),
    path('order/<int:order_id>/pay/', views.OrderPaymentView.as_view(), name='order_payment'),
    path('order/<int:order_id>/status/', views.UpdateOrderStatusView.as_view(), name='update_order_status'),
    path('product/<int:id>/', views.ProductDetailView.as_view(), name='product_detail'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('', include(auth_patterns)),  # Remove 'auth/' prefix
    path('', include(user_patterns)),
    path('', include(product_order_patterns)),
]