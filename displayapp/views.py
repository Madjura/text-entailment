from collections import defaultdict

from django.shortcuts import render

# Create your views here.
from displayapp.forms import QueryForm
from parse.parse import parse_query
from scaffidiapp.models import ProductFeatureScore, ProductFeatureScoreTop


def index(request):
    return render(request, "index.html", {"queryform": QueryForm()})


def query(request):
    if request.method == "POST":
        queryform = QueryForm(request.POST)
        if queryform.is_valid():
            q = queryform.cleaned_data["query"]
            min_relatedness = queryform.cleaned_data["min_relatedness"]
            max_path_length = queryform.cleaned_data["max_path_length"]
            max_paths = queryform.cleaned_data["max_paths"]
            paths = parse_query(q, min_relatedness, max_path_length, max_paths)
            feature2path = defaultdict(lambda: list())
            feature2products = {}
            for path in paths:
                for node in path:
                    explanation, subject, predicate, obj, target = node
                    if predicate == "has_product_feature" or predicate == "has_feature":
                        feature2path[obj[:-2]].append(path)
            for feature in feature2path.keys():
                products = ProductFeatureScore.objects.for_feature(feature, top=ProductFeatureScoreTop.objects.latest())
                feature2products[feature] = list(products)
            combined = defaultdict(lambda: list())
            for feature in feature2path.keys():
                combined[feature].append(feature2path[feature])
                combined[feature].append(feature2products[feature])
            combined = dict(combined)  # for template
            return render(request, "result.html", {"paths_features": combined, "queryform": queryform})
    queryform = QueryForm()
    return render(request, "result.html", {"queryform": queryform})