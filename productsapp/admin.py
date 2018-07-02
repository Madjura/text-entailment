from django.contrib import admin

# Register your models here.
from productsapp.models import Product, Review, Category

admin.site.register(Product)
admin.site.register(Review)
admin.site.register(Category)