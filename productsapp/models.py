import csv
import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, IntegrityError


class CategoryManager(models.Manager):
    def for_name(self, name):
        try:
            return self.get(name__iexact=name)
        except ObjectDoesNotExist:
            return []


class Category(models.Model):
    name = models.TextField()

    objects = CategoryManager()

    def __str__(self):
        return self.name


class ReviewManager(models.Manager):
    def for_category_name(self, name):
        return self.filter(product__category=Category.objects.get(name=name))

    def for_category(self, category):
        return self.filter(product__category=category)


class Product(models.Model):
    asin = models.TextField()
    name = models.TextField()
    url = models.TextField()
    category = models.ForeignKey(Category, default=1, on_delete=models.CASCADE)

    @staticmethod
    def from_json():
        with open("E:\\PycharmProjects\\text_entailment\\drills.json", "r") as f:
            j = json.loads(f.read())
        for i, d in enumerate(j):
            print(f"{i} out of {len(j)}")
            product = Product(asin=d["asin"], name=d["name"], url=d["url"])
            try:
                product = Product.objects.get(asin=d["asin"])
            except ObjectDoesNotExist:
                product.save()
            if d["review"]:
                Review.objects.create(product=product, text=d["review"], rating=d["rating"])

    @staticmethod
    def from_csv(path):
        c, _ = Category.objects.get_or_create(name="Phone")
        with open(path, "r", encoding="utf8") as f:
            r = csv.reader(f)
            for i, row in enumerate(r):
                print(f"{i} phone reviews processed")
                name, brand, price, rating, text, votes = row
                try:
                    product = Product.objects.get(name=name, category=c)
                except ObjectDoesNotExist:
                    product = Product.objects.create(asin=">KAGGLE. NO ASIN<", name=name, url=">KAGGLE. NO URL<",
                                                     category=c)
                try:
                    Review.objects.create(product=product, text=text, rating=rating)
                except ValueError:
                    continue  # happens for first row


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    review_id = models.TextField(null=True)
    text = models.TextField()
    rating = models.FloatField()

    objects = ReviewManager()