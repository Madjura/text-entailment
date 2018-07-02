from text_entailment import setup

setup()
from productsapp.models import Product

if __name__ == "__main__":
    path = "E:\\PycharmProjects\\text_entailment\\Amazon_Unlocked_Mobile.csv"
    Product.from_csv(path)