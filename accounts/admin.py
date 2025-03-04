from django.contrib import admin
from .models import CustomUser, Category, Brand, Product, Order, Message, Review

admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Message)
admin.site.register(Review)

admin.site.site_header = 'ladyfirst.me'
admin.site.site_title = 'ladyfirst.me'
admin.site.site_url = 'ladyfirst.me'