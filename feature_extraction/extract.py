import pickle
from collections import defaultdict
from math import sqrt

import langdetect
import numpy

from feature_extraction.scaffidi.scaffidi import get_wordcounts
from text_entailment import setup

setup()
import spacy
from bs4 import BeautifulSoup
# python -m spacy download en_core_web_sm
from django.db import transaction, IntegrityError, OperationalError, DataError

from productsapp.models import Review, Category, Product
from scaffidiapp.models import FeatureCountsTop, ReviewWordFrequency, FeatureCount, ProductFeatureScore
from langdetect import detect

english = spacy.load("en_core_web_sm")


def create_unigram_bigram_counts(unigram_counts, bigram_counts, feature_counts_top):
    """
    Creates FeatureCount objects for bigram and unigrams.

    :param unigram_counts: The unigrams, with frequency.
    :param bigram_counts: The bigrams with frequency.
    :param feature_counts_top: The FeatureCountsTop the FeatureCounts belong to.
    :return:
    """
    feature_counts = []
    unigram_count = 0
    ok_unigrams = get_wordcounts(unigram_counts.keys())
    for i, (unigram, count) in enumerate(unigram_counts.items()):
        if ok_unigrams[unigram]:
            feature_counts.append(FeatureCount(feature=unigram, bigram=False, count=count,
                                               feature_count=feature_counts_top))
            unigram_count += 1
        else:
            print(f"REJECTING UNIGRAM: {unigram}")
    print(f"UNIGRAMS OK: {unigram_count}")
    ok_bigrams = []
    for b in bigram_counts.keys():
        ok_bigrams.extend(b.split("<BIGRAM>"))
    ok_bigrams = get_wordcounts(list(set(ok_bigrams)))
    bigram_count = 0
    for i, (bigram, count) in enumerate(bigram_counts.items()):
        w = bigram.split("<BIGRAM>")
        if ok_bigrams[w[0]] or ok_bigrams[w[1]]:
            bigram_count += 1
            feature_counts.append(FeatureCount(feature=bigram, bigram=True, count=count,
                                               feature_count=feature_counts_top))
        else:
            print(f"REJECTING BIGRAM: {w}")
    print(f"BIGRAMS OK: {bigram_count}")
    for i, f in enumerate(feature_counts):
        print(f"Making feature count {i} out of {len(feature_counts)}")
        try:
            with transaction.atomic():
                f.save()
        except OperationalError:
            continue
        except DataError:
            print(f"{f.feature} <---- TOO LONG?")


def create_review_frequencies(word_freqs, review):
    """
    Creates ReviewWordFrequency instances.

    :param word_freqs: The frequencies of the words in the review.
    :param review: The review.
    :return:
    """
    with transaction.atomic():
        for token, freq in word_freqs.items():
            try:
                _, _created = ReviewWordFrequency.objects.get_or_create(review=review, term=token, frequency=freq)
            except IntegrityError:
                # can happen if the stripping of HTML is changed or texts are processed differently in the future
                f = ReviewWordFrequency.objects.get(review=review, term=token)
                f.frequency = freq
                f.save()
            except OperationalError:
                # this is caused by emojis, rather pointless as features anyway so they are thrown out
                continue
            except DataError:
                continue  # no idea why this can happen, said data too long


def strip_html(text):
    """
    Strips HTML from a text using BeautifulSoup4.

    :param text: The text that is to be stripped of HTML tags.
    :return: The text without HTML tags.
    """
    return BeautifulSoup(text, "html5lib").get_text()


def get_review_objects(category, limit=None):
    """
    Returns ProductFeedback objects that have both a rating in stars and a review text.

    :param category: Optional. The category the products the reviews belong to must have.
    :param limit: The maximum number of reviews to return.
    :return: A list containing the ProductFeedback objects.
    """
    print(f"Loading reviews for category {category}")
    reviews = []
    candidates = list(Review.objects.for_category(category))
    for i, r in enumerate(candidates):
        print(f"{i} out of {len(candidates)} reviews checked for language")
        text = strip_html(r.text)
        try:
            if not detect(text) == "en":
                continue
        except langdetect.lang_detect_exception.LangDetectException:
            print(f"WEIRD ERROR: {text}")
            continue
        reviews.append((r, text))
    print(len(reviews), " REVIEWS FOUND")
    if limit:
        return reviews[:limit]
    with open("reviewsFINE.p", "wb") as f:
        pickle.dump(reviews, f)
    return reviews


def spacy_feature_counts(category, limit=None, lang="en", lemmatized=False):
    """
    Uses spacy to POS tag the reviews and get the frequency counts for the reviews.

    :param category: The category of the reviews.
    :param limit: Optional. The maximum number of reviews to look at. Used for debugging only.
    :param lang: Optional. Default: "de". The language to be used. Currenty only German and English are supported.
    :param lemmatized: Optional. Default: False. Whether the tokens are to be lemmatized or not.
    :return:
    """
    reviews = get_review_objects(category, limit=limit)
    if not reviews:
        print(f"-->No reviews or predictions found for category {category}<--")
        return
    unigram_counts = defaultdict(int)
    bigram_counts = defaultdict(int)
    feature_counts_top = FeatureCountsTop.objects.create(language=lang, category=category)
    # feature_counts_top.reviews.set([x for x, _ in reviews])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[:100000]])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[100000:200000]])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[200000:300000]])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[300000:]])
    for i, (review_object, review_text) in enumerate(reviews):
        # data = json.loads(review_object.properties)
        # category = review_object.category
        print(f"POS-tag reviews: {i} out of {len(reviews)}")
        # strip html tags
        # review_text = strip_html(data["TEXT"])
        # only german for now
        doc = english(review_text)
        word_freqs = defaultdict(int)
        for sentence in list(doc.sents):
            bigram_noun_candidate = None
            for token in sentence:
                if token.pos_ in ["NOUN", "PRPN"]:
                    if lemmatized:
                        text = token.lemma_.lower()
                    else:
                        text = token.text.lower()
                    unigram_counts[text] += 1
                    if bigram_noun_candidate:
                        first, second = bigram_noun_candidate, text
                        bigram_counts[f"{first}<BIGRAM>{second}"] += 1
                    bigram_noun_candidate = text
                else:
                    bigram_noun_candidate = None
                # add to frequency dict here
                word_freqs[token.text] += 1
        # word frequency for review done, creating review frequency count
        create_review_frequencies(word_freqs, review_object)
    with open("unigramsALLNEW.p", "wb") as f:
        pickle.dump(unigram_counts, f)
    with open("bigramsALLNEW.p", "wb") as f:
        pickle.dump(bigram_counts, f)
    create_unigram_bigram_counts(unigram_counts, bigram_counts, feature_counts_top)


if __name__ == "__main__":
    c = Category.objects.for_name("Phone")
    # spacy_feature_counts(c, lemmatized=True, limit=None)
    FeatureCountsTop.objects.all().delete()
    reviews = get_review_objects(c)
    feature_counts_top = FeatureCountsTop.objects.create(language="en", category=c)
    feature_counts_top.reviews.add(*[x for x, _ in reviews[:100000]])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[100000:200000]])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[200000:300000]])
    feature_counts_top.reviews.add(*[x for x, _ in reviews[300000:]])
    # feature_counts_top = FeatureCountsTop.objects.latest("en", category=c)
    # for i, (x, _) in enumerate(reviews):
    #     print(f"Adding M2M {i} out of {len(reviews)}")
    #     feature_counts_top.reviews.add(x)
    with open("unigramsALLNEW.p", "rb") as f:
        unigrams = pickle.load(f)
    with open("bigramsALLNEW.p", "rb") as f:
        bigrams = pickle.load(f)
    create_unigram_bigram_counts(unigrams, bigrams, feature_counts_top)