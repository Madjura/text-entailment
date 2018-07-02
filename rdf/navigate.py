import pickle
from collections import defaultdict
from copy import deepcopy
from pprint import pprint

import rdflib
import spacy
from nltk.corpus import wordnet

from indra.indra import check_relatedness_pairs
from text_entailment import setup
from text_entailment.settings import EXTENDED_GRAPH_PATH

setup()

subject = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#subject')
predicate = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate')
obj = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#object')
type_ = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
map_ = {subject: "subject", predicate: "predicate", obj: "object", type_: "type"}


english = spacy.load("en_core_web_sm")


with open("E:\\PycharmProjects\\text_entailment\\wordnet\\wordnet_index_uniqueWTFIX.p", "rb") as f:
    wn = pickle.load(f)


def get_synsets_containing(node):
    node_name = node.split(".")[0]
    out = []
    for s in wordnet.synsets(node_name):
        total = "__".join(x.name() for x in s.lemmas())
        noun_or_verb = str(s).split(".")[1]
        if noun_or_verb == "n":
            out.append(total+".n")
        elif noun_or_verb == "v":
            out.append(total+".v")
    if not out:
        out = [node]
    return out


def get_role_nodes(g, node):
    names = []
    if node[-2:] == ".n":
        e = ".n"
        name = rdflib.term.URIRef(f"http://nlp/resources/synsets/WordNetNounSynset#{node[:-2]}")
    elif node[-2:] == ".v":
        e = ".v"
        name = rdflib.term.URIRef(f"http://nlp/resources/synsets/WordNetVerbSynset#{node[:-2]}")
    else:
        r1 = get_role_nodes(g, node+".n")
        r2 = get_role_nodes(g, node+".v")
        r1.extend(r2)
        return r1
    edges = g.edges(name, data=True)
    if not edges:
        name = rdflib.term.URIRef(f"http://nlp/resources/synsets/WordNetVerbSynset#{node[:-2]}")
    edges = g.out_edges(name, data=True)
    if not edges:
        vn = node[-2:]
        n = node[:-2]
        lemmas = []
        for s in wordnet.synsets(n):
            lemmas.extend([str(lemma.name()) for lemma in s.lemmas() if str(lemma.name()) != n])
        lemmas = list(set(lemmas))
        if not lemmas:
            return []
        if vn == ".v":
            names.extend([rdflib.term.URIRef(f"http://nlp/resources/synsets/WordNetVerbSynset#{n}__{lemma}") for lemma in lemmas])
        elif vn == ".n":
            names.extend([rdflib.term.URIRef(f"http://nlp/resources/synsets/WordNetNounSynset#{n}__{lemma}") for lemma in lemmas])
    if not names and (type(name) is str or type(name) is rdflib.term.URIRef):
        names = [name]
    role_nodes = []
    for name in names:
        full_name = str(name).split("#")[1]
        for syn in full_name.split("__"):
            role_nodes.append((full_name, full_name+e, "has_synonym", syn+e))
        edges = g.out_edges(name, data=True)
        if not edges:
            continue
        supertype = None
        spo = defaultdict(lambda: dict())
        for edge in edges:
            source, end, data = edge
            try:
                role_id, role = data["label"].split("__")
            except ValueError:
                if data["label"] == "has_feature":
                    feature = str(end).split("#")[1] + ".n"  # always a noun
                    role_nodes.append((str(name).split("#")[1], node, "has_feature", feature))
                continue
            spo[role_id][role] = end
            supertype = data["supertype"]
        role_nodes.append((str(name).split("#")[1], node, "supertype", str(supertype).split("#")[1]+e))
        for po in spo.values():
            s = str(po["subject"]).split("#")[1]
            p = str(po["predicate"]).split("#")[1]
            o = str(po["object"])
            role_nodes.append((str(name).split("#")[1], s, p, o))
    return role_nodes


def get_head_words(node, role):
    if len(node.split(" ")) == 1:
        return node
    doc = english(node)
    out = []
    for sentence in list(doc.sents):
        for token in sentence:
            if role == "supertype":
                return token.lemma_.lower()+".n"
            elif role == "has_diff_qual":
                if any(x in token.dep_ for x in ["subj", "obj", "mod"]):
                    out.append(f"{token.lemma_.lower()}.n")
            else:
                if token.dep_ == "ROOT":
                    # main verb
                    out.append(f"{token.lemma_.lower()}.v")
                if any(x in token.dep_ for x in ["subj", "obj"]):
                    out.append(f"{token.lemma_.lower()}.n")
    return out


def navigate(g, source, target, min_relatedness=0.15, max_path_length=6, m=3):
    print("SOURCE: ", source, " TARGET: ", target, " MIN: ", min_relatedness, " MAX: ", max_path_length, " M: ", m)
    paths = []
    stack = []
    new_path = [("source", "source", "source", "source", source)]
    stack.append(new_path)
    while stack and len(paths) < m:
        path = stack.pop()
        synset, s, path_role, n,  next_node = path[-1]
        if next_node in [target, target[:-2]]:
            if path not in paths:
                paths.append(path)
            continue
        while next_node not in [None, target, target[:-2]] and len(path) < max_path_length:
            synsets = get_synsets_containing(next_node)
            nodes = []
            feature_info = []
            for synset in synsets:
                role_nodes = deepcopy(feature_info)
                found_role_nodes = list(set(get_role_nodes(g, synset)))
                role_nodes.extend(found_role_nodes)
                if not role_nodes:
                    continue
                to_check = []
                to_check_pairs = []
                for equivalent_node, s, role, node in role_nodes:
                    t1 = " ".join(node.split(".")[0].split("_"))
                    t2 = " ".join(target.split(".")[0].split("_"))
                    # relatedness = check_relatedness(t1, t2)
                    to_check.append((t1, t2, next_node, synset, s, role, node))
                    to_check_pairs.append((t1, t2))
                if to_check_pairs:
                    scores = check_relatedness_pairs(to_check_pairs)
                    for t1, t2, next_node, _synset, s, role, node in to_check:
                        relatedness = scores[(t1, t2)]
                        if relatedness > min_relatedness:
                            if next_node == node:
                                # stop loops such as bread contained in BLA: bla -> supertype bread ->
                                # bread contained BLA2 -> supertype eat
                                continue
                            if role == "has_product_feature":
                                explanation = f"{next_node} has_product_feature -> {node}"
                            elif role == "has_feature":
                                explanation = f"{next_node} has product feature (scaffidi) -> {node}"
                            else:
                                explanation = f"{next_node} is contained in synset -> {_synset}"
                            nodes.append((
                                (explanation, s, role, node), relatedness)
                            )
            nodes = list(set(nodes))
            best_roles = sorted(nodes, key=lambda x: x[1], reverse=True)
            nodes = []
            head_words = []
            for best_role in best_roles:
                (synset, s, role, node), relatedness = best_role
                h = get_head_words(node, role)
                if type(h) is str:
                    h = [h]
                for head_word in h:
                    head_words.append((synset, s, role, node, head_word))
                # head_words.extend(h)
            nodes.extend(head_words)
            nodes = list(set(nodes))
            ranked_head_words = nodes  # already sorted from best_roles
            end = []
            for (synset, s, role, node, word) in ranked_head_words:
                new_path = deepcopy(path)
                if word == target[:-2] or word == target:
                    end.append((synset, s, role, node, word))
                else:
                    add_to_path = (synset, s, role, node, word)
                    if add_to_path not in new_path:
                        new_path.append((synset, s, role, node, word))
                        stack.append(new_path)
            for e in end:
                new_path = deepcopy(path)
                new_path.append(e)
                stack.append(new_path)
            try:
                synset, s, next_role, n, next_node = ranked_head_words[-1]
            except IndexError:
                # dead end
                break
            if end:
                synset, s, next_role, n, next_node = end[-1]  # cheat and use path with valid end first
            path.append((synset, s, next_role, n, next_node))
            if next_node == target[:-2] or next_node == target:
                paths.append(path)
    print("PATHS: ", paths)
    return paths


# test(g, "halberd.n", "kill.v")
# test(g, "camera.n", "picture.n")
# test(g, "battery.n", "electricity.n", min_relatedness=0.4)
# test(g, "electricity.n", "charge.v", min_relatedness=0.33)
# test(g, "battery.n", "charge.v", min_relatedness=0.33)
# test(g, "camera.n", "picture.n", min_relatedness=0.33)
# test(g, "phone.n", "picture.n", min_relatedness=0.33)
# test(g, "pie.n", "eat.v", min_relatedness=0.33)

# print("---NAVIGATE.PY-----")

# with open(EXTENDED_GRAPH_PATH, "rb") as f:
#    g = pickle.load(f)
# p = navigate(g, "hit.v", "injure.v", min_relatedness=0.25, m=1, max_path_length=5)
# print(p)
# navigate(g, "cellphone.n", "charge.v", min_relatedness=0.20, m=10)
# navigate(g, "cellphone.n", "lens.n", min_relatedness=0.20, m=2)

# p = navigate(g, "cellphone.n", "camera.n", min_relatedness=0.20, m=1)
# print(p)
# p = navigate(g, "camera.n", "picture.n", min_relatedness=0.20, m=3)
# print("---")
# print(p)
# p = navigate(g, "cellphone.n", "picture.n", min_relatedness=0.2, m=100)
# pprint(p)

# test(g, "alcoholic.n", "drink.v", min_relatedness=0.2)
# navigate()

# p = navigate(g, "cellphone.n", "picture.n", min_relatedness=0.20, m=1)
# print(p)# [[('source', 'source', 'source', 'source', 'cellphone.n'), ('cellphone.n has product feature (scaffidi) -> picture.n', 'cellular_telephone__cellular_phone__cellphone__cell__mobile_phone.n', 'has_feature', 'picture.n', 'picture.n')]]