import pickle
from collections import defaultdict

import spacy
from nltk.corpus import wordnet

english = spacy.load("en_core_web_sm")

def _pickle_fix():
    return list()


index = defaultdict(_pickle_fix)


all_synsets = list(wordnet.all_synsets())

m = {"NOUN": ".n", "VERB": ".v"}
m = defaultdict(lambda: "")
m["NOUN"] = ".n"
m["VERB"] = ".v"

for i, ss in enumerate(all_synsets):
    print(f"{i} out of {len(all_synsets)}")
    s = ss.name().split(".")
    name = s[0]
    t = s[1]
    if t not in ["v", "n"]:
        continue
    doc = english(ss.definition())
    for sentence in list(doc.sents):
        for token in sentence:
            index[token.lemma_.lower() + m[token.pos_]].append(f"{name}.{t}")

with open("wordnet_index_withWT.p", "wb") as f:
    pickle.dump(index, f)