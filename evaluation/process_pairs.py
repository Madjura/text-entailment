import itertools
import pickle
from collections import defaultdict
from math import log
from pprint import pprint

import spacy

from evaluation.load import load_bpi
from indra.indra import check_relatedness_pairs
from rdf.navigate import navigate
from text_entailment.settings import EXTENDED_GRAPH_PATH

pairs = load_bpi()
english = spacy.load("en_core_web_sm")
MIN_RELATEDNESS = 0.25

with open(EXTENDED_GRAPH_PATH, "rb") as f:
    g = pickle.load(f)

with open("E:\PycharmProjects\\text_entailment\wordnet\wordnet_index_freqs.p", "rb") as f:
    freqs = pickle.load(f)

metrics = {"YES": [0, 0], "NO": [0, 0]}
metrics_empty = {"YES": 0, "NO": 0}
m = {"NOUN": ".n", "VERB": ".v", "PROPN": ".n"}

IDF_LIMIT = 3
TOTAL_WN = freqs["WN_ALL_COUNT"]


for e, pp in pairs.items():
    todo = defaultdict(lambda: list())
    all_pairs = []
    nv_helper = defaultdict(lambda: dict())
    print(f"----PROCESSING FOR ENTAILMENT: {e} -----")
    for i, (text, hypothesis) in enumerate(pp):
        print(f"-PROCESSING PAIR {i} OUT OF {len(pp)}")
        t = english(text)
        h = english(hypothesis)
        t_processed = []
        h_processed = []
        nv = defaultdict(str)
        for sentence in list(t.sents):
            for token in sentence:
                freq = freqs[token.lemma_]
                if not freq:
                    freq = 1
                idf = log(TOTAL_WN / freq)
                if idf < IDF_LIMIT:
                    continue
                if token.pos_ == "NOUN" or token.pos_ == "VERB" or token.pos_ == "PROPN":
                    t_processed.append(token.lemma_)
                    nv[token.lemma_] = m[token.pos_]
        for sentence in list(h.sents):
            for token in sentence:
                freq = freqs[token.lemma_]
                if not freq:
                    freq = 1
                idf = log(TOTAL_WN / freq)
                if idf < IDF_LIMIT:
                    continue
                if token.pos_ == "NOUN" or token.pos_ == "VERB" or token.pos_ == "PROPN":
                    h_processed.append(token.lemma_)
                    nv[token.lemma_] = m[token.pos_]
        t_unique = set(t_processed).difference(set(h_processed))
        h_unique = set(h_processed).difference(set(t_processed))
        limit = max(len(t_unique), len(h_unique))
        check = list(itertools.product(t_unique, h_unique))
        all_pairs.extend(check)
        todo[(text, hypothesis, limit)] = check
        nv_helper[(text, hypothesis, limit)] = nv
    indra_scores = check_relatedness_pairs(list(set(all_pairs)))
    print(all_pairs)
    print("------------")
    for i, ((t, h, limit), ppairs) in enumerate(todo.items()):
        print(f"--PROCESSING TODO {i} OUT OF {len(todo)}")
        pprint(metrics)
        pair_scores = []
        nv = nv_helper[(t, h, limit)]
        for t1, t2 in ppairs:
            pair_scores.append((t1, t2, indra_scores[(t1, t2)]))
        pair_scores_sorted = sorted(pair_scores, key=lambda k: k[2], reverse=True)[:limit]
        if not pair_scores_sorted:
            metrics[e][1] += 1
            metrics_empty[e] += 1
            continue
        f = True
        no_path = 0
        lim = round((1/2)*len(pair_scores_sorted))
        for j, (t1, t2, score) in enumerate(pair_scores_sorted):
            t1 += nv[t1]
            t2 += nv[t2]
            print(f"PAIR SCORE {j} OUT OF {len(pair_scores_sorted)} - {t1} {t2}")
            p = navigate(g, t1, t2, min_relatedness=MIN_RELATEDNESS, m=1, max_path_length=5)
            if not p:
                no_path += 1
                if no_path > lim:
                    break
        if no_path <= lim:
            print(f"LIMIT: {lim} ENTAILMENT FOUND: {no_path} TOTAL {len(pair_scores_sorted)}")
            metrics[e][0] += 1  # entailment considered to be found
        else:
            print(f"{lim} ENTAILMENT NOT FOUND: {no_path} TOTAL {len(pair_scores_sorted)}")
            metrics[e][1] += 1  # no entailment
# with open("metrics.p", "wb") as f:
#     pickle.dump(metrics, f)
# with open("metrics_empty.p", "wb") as f:
#     pickle.dump(metrics_empty, f)
