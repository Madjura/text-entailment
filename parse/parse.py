import pickle

import spacy

from rdf.navigate import navigate
from text_entailment.settings import EXTENDED_GRAPH_PATH

english = spacy.load("en_core_web_sm")

q1 = "Which phones take the best pictures?"
q2 = "Which phones charge the fastest?"
q3 = "Which phone has the best screen?"
# q4 = "Which phone is the fastest?"  # <-- bad, need to know that it is about speed
q5 = "Which phone has the fastest processor?"
q6 = "Which phones fly the furthest?"


with open(EXTENDED_GRAPH_PATH, "rb") as f:
    g = pickle.load(f)


def parse_query(query, min_relatedness, max_path_length, max_paths):
    d = english(query)
    for sentence in list(d.sents):
        category = None
        root = None
        target_feature = None
        for token in sentence:
            if token.dep_ == "nsubj":
                category = token.lemma_ + ".n"
            elif token.dep_ == "ROOT":
                root = token.lemma_
            elif token.dep_ == "dobj":
                # if noun, it is the feature
                # if not, then root is the feature
                # example:
                # Which det ADJ
                # phones nsubj NOUN
                # charge ROOT VERB
                # the det DET
                # fastest dobj ADJ
                # ? punct PUNCT
                #
                # Which det ADJ
                # phone nsubj NOUN
                # has ROOT VERB
                # the det DET
                # fastest amod ADJ
                # processor dobj NOUN
                # ? punct PUNCT
                if token.pos_ == "NOUN":
                    target_feature = token.lemma_ + ".n"
                else:
                    target_feature = root + ".v"
            print(token, token.dep_, token.pos_)
        print(f"Category: {category}, target feature: {target_feature}, root: {root}")
        if not target_feature:
            target_feature = root
        return navigate(g, category, target_feature, min_relatedness=min_relatedness, max_path_length=max_path_length,
                        m=max_paths)
