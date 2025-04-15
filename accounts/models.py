from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    full_address = models.TextField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    chest_bust = models.FloatField(null=True, blank=True)
    waist = models.FloatField(null=True, blank=True)
    hip = models.FloatField(null=True, blank=True)
    inseam = models.FloatField(null=True, blank=True)
    foot_size_us = models.FloatField(null=True, blank=True)
    is_setup_complete = models.BooleanField(default=False)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email or self.phone_number or self.username

    def save(self, *args, **kwargs):
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone number must be provided.")

        # Normalize phone number
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ", "").replace("-", "")

        # Validate float fields
        float_fields = [
            'weight_kg', 'height_cm', 'chest_bust', 'waist',
            'hip', 'inseam', 'foot_size_us'
        ]
        for field in float_fields:
            value = getattr(self, field)
            if value is not None and value < 0:
                raise ValueError(f"{field} must be a positive number.")

        super().save(*args, **kwargs)

# ... other imports and models remain unchanged ...

class OTPCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    identifier = models.CharField(max_length=255, null=True, blank=True)  # New field
    code = models.CharField(max_length=6, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OTP for {self.identifier or self.user.email or self.user.phone_number}: {self.code}"

class Category(models.Model):
    title = models.CharField(max_length=255, unique=True)
    category_slug = models.SlugField(max_length=255, unique=True, blank=True)
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
    image = models.ImageField(upload_to='products/', null=True, blank=True)  # Made nullable for development

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

    class Meta:
        unique_together = ('buyer', 'product')  # Note: This may cause IntegrityError during testing

    def save(self, *args, **kwargs):
        self.total_price = self.product.second_hand_price * self.quantity
        super().save(*args, **kwargs)

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

class Review(models.Model):
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    comment = models.TextField()
    title = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reviewer', 'seller')  # Note: This may cause IntegrityError during testing

class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reset token for {self.user.email}"