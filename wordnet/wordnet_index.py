import pickle

def _pickle_fix():
    return list()

with open("wordnet_index_withWT.p", "rb") as f:
    i = pickle.load(f)

n = {}
for k, v in i.items():
    n[k] = list(set(v))
with open("wordnet_index_uniqueWTFIX.p", "wb") as f:
    pickle.dump(n, f)