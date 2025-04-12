from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

# Custom user model
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True) 
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True) 
    phone_number = models.CharField(max_length=20, unique=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True) 
    city = models.CharField(max_length=100, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  

    def __str__(self):
        return self.email  


# Category model
class Category(models.Model):
    title = models.CharField(max_length=255, unique=True)
    category_slug = models.SlugField(max_length=255, unique=True, blank=True)  # Auto-generated if blank
    image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.category_slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            count = 1
            while Category.objects.filter(category_slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{count}"
                count += 1
            self.category_slug = unique_slug
        super().save(*args, **kwargs)


# Brand model
class Brand(models.Model):
    title = models.CharField(max_length=255, unique=True)
    brand_slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "brands"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.brand_slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            count = 1
            while Brand.objects.filter(brand_slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{count}"
                count += 1
            self.brand_slug = unique_slug
        super().save(*args, **kwargs)


# Product model
class Product(models.Model):
    CONDITION_CHOICES = [
        ('brand_new', 'Brand New'),
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('gently_used', 'Gently Used'),
        ('worn', 'Worn'),
        ('heavily_used', 'Heavily Used'),
    ]

    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'X-Large'),
        ('XXL', 'XX-Large'),
        ('custom', 'Custom'),
    ]

    COLOR_CHOICES = [
        ('yellow', 'Yellow'),
        ('red', 'Red'),
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('orange', 'Orange'),
        ('purple', 'Purple'),
        ('pink', 'Pink'),
        ('brown', 'Brown'),
        ('black', 'Black'),
        ('white', 'White'),
        ('gray', 'Gray'),
        ('teal', 'Teal'),
        ('cyan', 'Cyan'),
        ('magenta', 'Magenta'),
    ]
    
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    product_slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    second_hand_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='gently_used')
    size = models.CharField(max_length=100, choices=SIZE_CHOICES, default='M')
    color = models.CharField(max_length=255, choices=COLOR_CHOICES, default='white')
    authenticity_document = models.FileField(upload_to='authenticity_documents/', null=True, blank=True)
    image = models.ImageField(upload_to='products/', default='default_product.jpg')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "products"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.product_slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            count = 1
            while Product.objects.filter(product_slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{count}"
                count += 1
            self.product_slug = unique_slug
        super().save(*args, **kwargs)


# Order model
class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]
    
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.total_price = self.product.second_hand_price * self.quantity
        super().save(*args, **kwargs)


# Message model
class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


# Review model
class Review(models.Model):
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    comment = models.TextField()
    title = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reviewer', 'seller')


# accounts/models.py
from django.db import models
from django.utils import timezone
from .models import CustomUser  # Already imported

class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=1)  # 1-hour validity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reset token for {self.user.email}"