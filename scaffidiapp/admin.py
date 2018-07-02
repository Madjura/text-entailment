from django.contrib import admin

# Register your models here.
from scaffidiapp.models import ReviewWordFrequency, ProductFeatureScore, ProductFeatureScoreTop

admin.site.register(ReviewWordFrequency)


class ProductFeatureScoreAdmin(admin.ModelAdmin):
    fields = ("feature", "score", "modified_score", "confidence", "num_reviews")
    readonly_fields = ("product", "reviews", "top")


admin.site.register(ProductFeatureScore, ProductFeatureScoreAdmin)
admin.site.register(ProductFeatureScoreTop)