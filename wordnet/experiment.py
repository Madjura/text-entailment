from nltk.corpus import wordnet

for s in wordnet.synsets("red_snapper"):
    print([str(lemma.name()) for lemma in s.lemmas()])
    print("----")

for s in wordnet.synsets("clown_anemone_fish"):
    print([str(lemma.name()) for lemma in s.lemmas()])
    print("----")

for s in wordnet.synsets("eelpout"):
    print([str(lemma.name()) for lemma in s.lemmas()])
    print("----")