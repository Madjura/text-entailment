import pickle
from collections import defaultdict

import spacy
from nltk.corpus import wordnet

english = spacy.load("en_core_web_sm")

index = defaultdict(int)

all_synsets = list(wordnet.all_synsets())

for i, ss in enumerate(all_synsets):
    print(f"{i} out of {len(all_synsets)}")
    s = ss.name().split(".")
    name = s[0]
    index["WN_ALL_COUNT"] += 1
    doc = english(ss.definition())
    doc_words = []
    for sentence in list(doc.sents):
        for token in sentence:
            doc_words.append(token.lemma_.lower())
    doc_words = list(set(doc_words))
    for w in doc_words:
        index[w] += 1

with open("wordnet_index_freqs.p", "wb") as f:
    pickle.dump(index, f)