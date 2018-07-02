import itertools
import math
import operator
import pickle
import pprint
from collections import defaultdict

import MySQLdb
import numpy
from django.db import transaction

from text_entailment import setup

setup()
from scaffidiapp.models import FeatureCountsTop, FeatureCount, ReviewWordFrequency, ProductFeatureScoreTop, \
    ProductFeatureScore
from productsapp.models import Category, Review

HOST = "127.0.0.1"
USER = "root"
PASSWORD = "password"
DB = "eng_wikipedia_2016_1M"


def get_total_words_count_wikipedia():
    """
    Gets the total size of the dictionary for Wikipedia.

    :return:
    """
    db = MySQLdb.connect(host=HOST, user=USER, password=PASSWORD, db=DB)
    dbc = db.cursor(MySQLdb.cursors.DictCursor)
    dbc.execute("SELECT COUNT(*) AS c FROM words")
    for row in dbc.fetchall():
        return row["c"]


def get_wordcounts(words):
    """
    Extracts word frequencies for words from the Wikipedia word frequency database.

    :param words: A list of words.
    :return: A dictionary mapping the words to their frequency.
    """
    db = MySQLdb.connect(host=HOST, user=USER, password=PASSWORD, db=DB)
    dbc = db.cursor(MySQLdb.cursors.DictCursor)
    db.set_character_set('utf8')
    dbc.execute('SET NAMES utf8;')
    dbc.execute('SET CHARACTER SET utf8;')
    dbc.execute('SET character_set_connection=utf8;')
    format_strings = ",".join(["%s"] * len(words))
    dbc.execute("SELECT * FROM words WHERE lower(word) IN (%s)" % format_strings, words)
    freq = defaultdict(int)
    for row in dbc.fetchall():
        row_dict = defaultdict(int, row)
        word = row_dict["word"].lower()
        row_freq = row_dict["freq"]
        word_freq = int(freq[word])
        freq[word] = row_freq if row_freq > word_freq else word_freq
    dbc.execute("SELECT COUNT(freq) as c FROM words")
    return freq


def get_wordcounts_german_bigrams(bigrams):
    """
    Extracts bigram counts from the Wikipedia word frequency database by using multiple small queries.

    :param bigrams:
    :return:
    """
    try:
        with open("bigrams_freq_wikipedia_OLD.p", "rb") as ff:
            return pickle.load(ff)
    except FileNotFoundError:
        pass
    db = MySQLdb.connect(host=HOST, user=USER, password=PASSWORD, db=DB)
    dbc = db.cursor(MySQLdb.cursors.DictCursor)
    db.set_character_set('utf8')
    dbc.execute('SET NAMES utf8;')
    dbc.execute('SET CHARACTER SET utf8;')
    w_ids = []
    bigram_counts = defaultdict(int)
    dbc.execute('SET character_set_connection=utf8;')
    i = 0
    for word1_, word2_ in bigrams:
        i += 1
        print("{} out of {} bigram frequency counts done".format(i, len(bigrams)))
        word1 = word1_.lower()
        word2 = word2_.lower()
        if not (word1 or word2):
            continue
        dbc.execute("SELECT * FROM words WHERE lower(word)=%s", (word1,))
        w1_rows = dbc.fetchall()
        w1_ids = []
        w1_id = None
        for row in w1_rows:
            row_dict = defaultdict(int)
            for k, v in row.items():
                row_dict[k] = v
            w1_id = int(row_dict["w_id"])
            w1_ids.append(w1_id)
        dbc.execute("SELECT * FROM words WHERE lower(word)=%s", (word2,))
        w2_rows = dbc.fetchall()
        w2_ids = []
        w2_id = None
        for row2 in w2_rows:
            row_dict = defaultdict(int)
            for k, v in row2.items():
                row_dict[k] = v
            w2_id = int(row_dict["w_id"])
            w2_ids.append(w2_id)
        if not (w1_rows or w2_rows):
            continue
        if len(w1_ids) >= len(w2_ids):
            perms = [zip(x, w2_ids) for x in itertools.permutations(w1_ids, len(w2_ids))]
        else:
            perms = [zip(x, w1_ids) for x in itertools.permutations(w2_ids, len(w1_ids))]
        perms = [item for sublist in perms for item in sublist]
        for w1_candidate, w2_candidate in perms:
            w_ids.append((w1_id, w2_id))
            dbc.execute("SELECT * FROM co_n WHERE (w1_id=%s AND w2_id=%s) OR (w1_id=%s AND w2_id=%s)", (w1_candidate, w2_candidate, w2_candidate, w1_candidate))
            for row in dbc.fetchall():
                row_dict = defaultdict(int)
                for k, v in row.items():
                    row_dict[k] = v
                freq = int(row_dict["freq"])
                bigram_counts[(word1, word2)] += freq
    with open("bigrams_freq_wikipedia_OLD.p", "wb") as ff:
        pickle.dump(bigram_counts, ff, pickle.HIGHEST_PROTOCOL)
    return bigram_counts


def scaffidi(unigram_freqs, bigram_freqs, unigram_mapping=None, bigram_mapping=None):
    """
    Calculates Scaffidi score for unigrams and bigrams.

    :param unigram_freqs: The unigrams with frequency.
    :param bigram_freqs: The bigrams with frequency.
    :param unigram_mapping: Mapping of unigram features to corresponding model objects.
    :param bigram_mapping: Mapping of bigram features to corresponding model objects.
    :return:
    """
    N = get_total_words_count_wikipedia()
    bigrams_list = []
    for bigrams, _ in bigram_freqs.items():
        bigrams_list.append(bigrams.split("<BIGRAM>"))
    word_freqs = get_wordcounts([x for x, _ in unigram_freqs.items()])
    bi_freqs = get_wordcounts_german_bigrams(bigrams_list)
    scaff = {}
    # handle unigram frequencies, calculate score and save
    i = 0
    unigram_px_average = sum(unigram_freqs.values()) / len(unigram_freqs)
    with transaction.atomic():
        for feature, freq in unigram_freqs.items():
            i += 1
            if not feature:
                continue
            nx = freq
            px = word_freqs[feature] / N
            if not px:
                px = unigram_px_average
            score = (nx - px*N) - (nx * math.log((nx/px*N))) - (math.log(nx)/2)
            scaff[feature] = score
            unigram_mapping[feature].scaffidi_score = score
            unigram_mapping[feature].save()
    # bigram frequencies
    i = 0
    bigram_px_average = sum(bigram_freqs.values()) / len(bigram_freqs)
    with transaction.atomic():
        for bigram_feature, freq in bigram_freqs.items():
            i += 1
            w1, w2 = bigram_feature.split("<BIGRAM>")
            if not (w1 or w2):
                continue
            nx = freq
            bi_freq = bi_freqs[(w1, w2)]
            if not bi_freq:
                bi_freq = bi_freqs[(w2, w1)]
            px = bi_freq / N
            if not px:
                px = bigram_px_average
            score = (nx - px*N) - (nx * math.log((nx/px*N))) - (math.log(nx)/2)
            scaff[f"{w1}<BIGRAM>{w2}"] = score
            bigram_mapping[f"{w1}<BIGRAM>{w2}"].scaffidi_score = score
            bigram_mapping[f"{w1}<BIGRAM>{w2}"].save()
    pprint.pprint(sorted(scaff.items(), key=operator.itemgetter(1)))


def filter_unigrams_bigrams(unigram_freqs, bigram_freqs):
    """
    Filters the unigrams and bigrams by the sqrt of the average frequency.

    :param unigram_freqs:
    :param bigram_freqs:
    :return:
    """
    unigram_minimum = round(math.sqrt(sum(unigram_freqs.values()) / len(unigram_freqs)))
    bigram_minimum = round(math.sqrt(sum(bigram_freqs.values()) / len(bigram_freqs)))
    print(f"Unigram length before filter: {len(unigram_freqs)}")
    unigram_freqs = {key: value for key, value in unigram_freqs.items() if value >= unigram_minimum}
    print(f"Bigram length before filter: {len(bigram_freqs)}")
    bigram_freqs = {key: value for key, value in bigram_freqs.items() if value >= bigram_minimum}
    print(f"Unigram length after filter: {len(unigram_freqs)}")
    print(f"Bigram length after filter: {len(bigram_freqs)}")
    return unigram_freqs, bigram_freqs


def scaffidi_from_db(lang="en", filter_freqs=True):
    """
    Performs Scaffidi score calculation using the previously calculated noun and proper noun frequencies from the
    database.

    :param lang: Optional. Default: "de". The language of the reviews.
    :param filter_freqs: Optional. Default: True. Whether the frequencies are to be filtered or used as-os.
    :return:
    """
    top = FeatureCountsTop.objects.latest(lang=lang)
    unigrams = FeatureCount.objects.unigrams(top)
    bigrams = FeatureCount.objects.bigrams(top)
    unigram_freqs = {unigram.feature: unigram.count for unigram in unigrams}
    bigram_freqs = {bigram.feature: bigram.count for bigram in bigrams}
    unigram_mapping = {unigram.feature: unigram for unigram in unigrams}
    bigram_mapping = {bigram.feature: bigram for bigram in bigrams}
    if filter_freqs:
        unigram_freqs, bigram_freqs = filter_unigrams_bigrams(unigram_freqs, bigram_freqs)
    scaffidi(unigram_freqs, bigram_freqs, unigram_mapping, bigram_mapping)


def get_top_features(category, limit=None, lang="en", top=None, unigram_only=False):
    """
    Returns the top features.

    :param category: The category for which the top features are to be selected.
    :param limit: The number of features to return at most.
    :param lang: Optional. Default: "de". The language of the reviews.
    :return: The top K features.
    """
    if top:
        latest = top
    else:
        latest = FeatureCountsTop.objects.latest(lang, category=category)
    if unigram_only:
        tops = FeatureCount.objects.filter(scaffidi_score__isnull=False, feature_count=latest, bigram=False).order_by("scaffidi_score")
    else:
        tops = FeatureCount.objects.filter(scaffidi_score__isnull=False, feature_count=latest).order_by("scaffidi_score")
    if limit:
        features = list(tops[:limit])
    else:
        features = list(tops)
    return features


def spacy_feature_rating(features):
    """
    Calculates the rating of the products based on the Scaffidi score and their reviews.

    :param features: The features that are to be considered for the products.
    :return:
    """
    review_feature_ratings = defaultdict(lambda: list())
    ff = [x.feature for x in features]
    frequencies = ReviewWordFrequency.objects.filter(term__in=ff).values_list("term", "frequency", "review")
    num = frequencies.count()
    print(f"Num of frequency instances: {num}")
    for i, (term, frequency, review) in enumerate(frequencies):
        print(f"{i} out of {num} frequencies handled")
        weight = 2 - 2 ** (1 - frequency)
        review_feature_ratings[Review.objects.get(pk=review)].append((term, weight))
    """
    for i, feature in enumerate(features):
        # TODO: need the reviews where feature has frequency 0 as well here
        frequencies = ReviewWordFrequency.objects.for_term(feature)
        for review_freq in frequencies:
            weight = 2 - 2 ** (1 - review_freq.frequency)
            review_feature_ratings[review_freq.review].append((feature, weight))
    """
    product_review_count = defaultdict(int)
    product_mapping_helper = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for i, (review, weights) in enumerate(review_feature_ratings.items()):
        print(f"Calculating feature score for {i} out of {len(review_feature_ratings)}")
        rating = review.rating
        product_review_count[review.product] += 1
        for feature, weight in weights:
            product_mapping_helper[review.product][feature]["NUMERATOR"] += weight * rating
            product_mapping_helper[review.product][feature]["DENOMINATOR"] += weight
            # the dict has a weird structure, the other values need to be floats and these ones list
            try:
                product_mapping_helper[review.product][feature]["REVIEWS"].append(review)
            except AttributeError:
                product_mapping_helper[review.product][feature]["REVIEWS"] = [review]
            try:
                product_mapping_helper[review.product][feature]["RATINGS"].append(rating)
            except AttributeError:
                product_mapping_helper[review.product][feature]["RATINGS"] = [rating]
    counts = sorted(set(list(product_review_count.values())))
    # lowest number of reviews a product has
    min_reviews = min(product_review_count.values()) or 0
    # highest number of reviews a product has
    max_reviews = max(product_review_count.values()) or 1
    highest = counts[round(len(counts) * 0.5)]
    second = counts[round(len(counts) * 0.1)]
    middle = counts[round(len(counts) * 0.05)]
    s_low = counts[round(len(counts) * 0.01)]
    print(f"Min: {min_reviews}, Max: {max_reviews}")
    print(f"Highest: {highest}, second: {second}, middle: {middle}, s_low: {s_low}")
    print("-->Committing ProductFeatureScores to database<--")
    top = ProductFeatureScoreTop.objects.create()
    with transaction.atomic():
        for i, (product, feature_dict) in enumerate(product_mapping_helper.items()):
            print(f"{i} out of {len(product_mapping_helper.items())} ProductFeatureScores commited to db")
            review_count = product_review_count[product]
            if review_count >= round(highest):
                mult = 1
            elif review_count >= round(second):
                mult = 0.75
            elif review_count >= round(middle):
                mult = 0.5
            elif review_count >= round(s_low):
                mult = 0.25
            else:
                mult = 0.1
            # normalized_review_count = review_count / max_reviews
            # print(f"Normalized experiment: {normalized_review_count}")
            for feature, num_or_denom_or_reviews in feature_dict.items():
                numerator = num_or_denom_or_reviews["NUMERATOR"]
                denominator = num_or_denom_or_reviews["DENOMINATOR"]
                reviews = set(num_or_denom_or_reviews["REVIEWS"])
                num_reviews = len(reviews)
                ratings = numpy.asarray(num_or_denom_or_reviews["RATINGS"])
                std = ratings.std()
                confidence = 1 - (std / (2 * math.sqrt(denominator)))
                score = (numerator / denominator)
                modified_score = score * mult
                product_feature_score = ProductFeatureScore.objects.create(
                    product=product, feature=feature, top=top, confidence=confidence, num_reviews=num_reviews)
                product_feature_score.score = score
                product_feature_score.modified_score = modified_score
                product_feature_score.save()
                product_feature_score.reviews.add(*reviews)


if __name__ == "__main__":
    # scaffidi_from_db(filter_freqs=False)
    c = Category.objects.for_name("Phone")
    features = get_top_features(c, limit=100, unigram_only=True)
    # for f in features:
    #     print(f.feature, f.scaffidi_score)
    # print("FOO")
    spacy_feature_rating(features)
    # for p in ProductFeatureScore.objects.filter(top=ProductFeatureScoreTop.objects.latest()):
    #     print(p.feature, p.score)
    # print(ProductFeatureScore.objects.filter(top=ProductFeatureScoreTop.objects.latest()).count())
