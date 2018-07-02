"""ScaffidiApp models."""
from django.db import models
from django.db.models import Q, Count

from productsapp.models import Product, Category, Review


class ProductFeatureScoreTopManager(models.Manager):
    def latest(self):
        """
        Returns the most recently created ProductFeatureScoreTop instance for a given language.

        :return: The most recently created ProductFeatureScoreTop instance for a given language.
        """
        # get most recent by creation date
        by_date = self.all().order_by("-created_at")
        l = by_date[0]
        featurescores = ProductFeatureScore.objects.filter(top=l)
        # if there are no FeatureCount instances for the given top (because processing was cancelled)  then check next
        if not featurescores.count():
            # set to empty queryset if nothing is found
            l = self.none()
            # index 0 was checked, start at 1 and check
            for i in range(1, len(by_date)):
                featurescores = ProductFeatureScore.objects.filter(top=by_date[i])
                if featurescores.count():
                    l = by_date[i]
                    break
        return l


class ProductFeatureScoreManager(models.Manager):
    """Manager for ProductFeatureScore."""

    def all_features(self, category=None):
        """Returns all unique features."""
        if category:
            c = Category.objects.for_name(category)
            if not c:
                return []
            q = self.filter(product__category=c, score__isnull=False, top=ProductFeatureScoreTop.objects.latest()).order_by().values_list("feature", flat=True).distinct()
            return list(q)
        return self.order_by().values_list("feature", flat=True).distinct()

    def for_feature(self, feature, order=True, top=None, category="Phone"):
        """
        Returns all ProductFeatureScores for a given feature.

        :param feature: The feature.
        :param order: Optional. Default: True. Whether the objects are to be ordered by score or not.
        :param top: Optional. Must be a ProductFeatureScoreTop instance. Used to filter out all instances that do not
            the specified ProductFeatureScoreTop set.
        :param category: Optional. Default: Phone. The category of the products.
        :return:
        """
        qs = self.filter(feature=feature).select_related("product").prefetch_related("reviews")
        c = Category.objects.for_name(category)
        qs.filter(product__category=c)
        if top:
            qs = qs.filter(top=top)
        if order:
            return qs.order_by("-modified_score", "-num_reviews")
        else:
            return qs

    def most_reviews(self):
        """Returns ProductFeatureScores ordered by number of reviews, descending."""
        return self.filter().annotate(num_reviews=Count("reviews")).order_by("-num_reviews")


class ReviewWordFrequencyManager(models.Manager):
    """Manager for RevieWordFrequency model."""

    def for_term(self, term):
        """
        Returns all ReviewWordFrequency instances for a given term.

        :param term: The term.
        :return: A queryset containing all ReviewWordFrequency instances for a given term.
        """
        return self.filter(term=term).select_related("review", "review__product")


class FeatureCountsTopManager(models.Manager):
    """Manager for FeatureCountsTop model."""

    def latest(self, lang, category=None):
        """
        Returns the most recently created FeatureCountsTop instance for a given language.

        :param lang: The language.
        :param category: Optional. The Category to filter for.
        :return: The most recently created FeatureCountsTop instance for a given language.
        """
        # get most recent by creation date
        by_date = self.filter(language=lang).order_by("-created_at")
        if category:
            by_date = by_date.filter(category=category)
        l = by_date[0]
        reviewfreqs = FeatureCount.objects.filter(feature_count=l)
        # if there are no FeatureCount instances for the given top (because processing was cancelled)  then check next
        if not reviewfreqs.count():
            # set to empty queryset if nothing is found
            l = self.none()
            # index 0 was checked, start at 1 and check
            for i in range(1, len(by_date)):
                reviewfreqs = FeatureCount.objects.filter(feature_count=by_date[i])
                if category:
                    reviewfreqs = reviewfreqs.filter(feature_count__category=category)
                if reviewfreqs.count():
                    l = by_date[i]
                    break
        return l


class FeatureCountManager(models.Manager):
    """Manager for FeatureCount model."""

    def bigrams(self, top):
        """
        Returns all FeatureCount instances for a given FeatureCountsTop that are bigrams.

        :param top: The FeatureCountsTop instance the FeatureCount instances belong to.
        :return: All FeatureCount instances for a given FeatureCountsTop that are bigrams.
        """
        return self.filter(Q(bigram=True) & Q(feature_count=top))

    def unigrams(self, top):
        """
        Returns all FeatureCount instances for a given FeatureCountsTop that are unigrams.

        :param top: The FeatureCountsTop instance the FeatureCount instances belong to.
        :return: All FeatureCount instances for a given FeatureCountsTop that are unigrams.
        """
        return self.filter(Q(bigram=False) & Q(feature_count=top))


class FeatureCountsTop(models.Model):
    """
    Top / "Meta" model for FeatureCount.
    Each instance represents one "run" of the feature count processing.
    """
    reviews = models.ManyToManyField(Review)
    created_at = models.DateTimeField(auto_now=True)
    language = models.CharField(max_length=10, default="de")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)

    objects = FeatureCountsTopManager()

    def __str__(self):
        return f"{self.created_at} - {self.language} - {self.category}"


class FeatureCount(models.Model):
    """Model representing found features in reviews, based on Scaffidi et. al."""
    feature = models.CharField(max_length=300)
    bigram = models.BooleanField()
    count = models.IntegerField()
    feature_count = models.ForeignKey(FeatureCountsTop, on_delete=models.CASCADE)
    scaffidi_score = models.FloatField(null=True)

    objects = FeatureCountManager()

    def __str__(self):
        return f"{self.feature}: {self.count}"


class ReviewWordFrequency(models.Model):
    """Model representing a frequency index of a review."""
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    term = models.CharField(max_length=300)
    frequency = models.IntegerField()
    feature_score = models.FloatField(null=True)

    objects = ReviewWordFrequencyManager()

    class Meta:
        unique_together = ("review", "term")


class ProductFeatureScoreTop(models.Model):
    """
    Top / "Meta" model of ProductFeatureScore.
    Each instance represents one "run" of the product feature score calculation.
    """
    created_at = models.DateTimeField(auto_now=True)

    objects = ProductFeatureScoreTopManager()


class ProductFeatureScore(models.Model):
    """Model representing the feature score of a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    feature = models.CharField(max_length=300)
    score = models.FloatField(null=True)
    modified_score = models.FloatField(null=True)
    confidence = models.FloatField(null=True)
    num_reviews = models.IntegerField(null=True)
    reviews = models.ManyToManyField(Review)
    top = models.ForeignKey(ProductFeatureScoreTop, on_delete=models.CASCADE, null=True)

    objects = ProductFeatureScoreManager()

    @property
    def product_reviews(self):
        """

        :return: The total number of reviews that the corresponding product has.
        """
        return Review.objects.filter(product=self.product).count()
