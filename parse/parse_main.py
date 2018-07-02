from pprint import pprint

from text_entailment import setup

setup()
from scaffidiapp.models import ProductFeatureScore

if __name__ == "__main__":
    features = ProductFeatureScore.objects.all_features(category="Phone")
    pprint([x.lower() for x in features])