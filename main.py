import json

from text_entailment import setup

setup()
from productsapp.models import Review, Product
from scaffidiapp.models import ProductFeatureScore, ProductFeatureScoreTop, FeatureCount

if __name__ == "__main__":
    reviews = Review.objects.all()
    products = Product.objects.all()
    print("Total reviews: ", reviews.count())
    print("Total products: ", products.count())
    with open("E:\PycharmProjects\\text_entailment\\amazon\drills.json", "r") as f:
        drills = json.loads(f.read())
    names = []
    for d in drills:
        names.append(d["name"])
    print("Number of reviews in drills: ", len(names))
    names = list(set(names))
    print("Total number of drill products: ", len(names))
    f = [(x.feature, x.scaffidi_score) for x in list(FeatureCount.objects.filter(bigram=False).order_by("scaffidi_score"))[:10]]
    print("FOO!")