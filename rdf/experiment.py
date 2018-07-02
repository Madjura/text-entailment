import pickle
from collections import defaultdict

import rdflib
from rdflib import Namespace, URIRef

from text_entailment import setup
import networkx as nx

from text_entailment.settings import EXTENDED_GRAPH_PATH, GRAPH_PATH

setup()
from scaffidiapp.models import ProductFeatureScore

g = rdflib.Graph()


try:
    print("OPENING FROM PICKLE ORIGINAL FILE")
    with open("graphFEATURES2.p", "rb") as f:
        g = pickle.load(f)
except FileNotFoundError:
    print("PARSING, PICKLE NOT FOUND, ORIGINAL FILE")
    g.parse(GRAPH_PATH, format="xml")
    with open("graphFEATURES2.p", "wb") as f:
        pickle.dump(g, f)

features = ProductFeatureScore.objects.all_features(category="Phone")
n = Namespace("http://nlp/resources/features#")

tmp = []
for f in features:
    tmp.append(f.lower())
new_nodes = []
tmp = list(set(tmp))
for f in tmp:
    new_nodes.append(URIRef("http://nlp/resources/features#" + f))

initial = rdflib.term.URIRef(
    "http://nlp/resources/synsets/WordNetNounSynset#cellular_telephone__cellular_phone__cellphone__cell__mobile_phone")

for f in new_nodes:
    g.add((initial, n.has_feature, f))
g.serialize(destination='outputNEW.ttl', format='turtle')
query = """
select ?synset ?sub ?pred ?obj ?super where {
         ?synset rdf:type ?node ;
                 dsr:has_supertype ?super .
         ?node rdf:subject ?sub ;
            rdf:predicate ?pred ;
            rdf:object ?obj .
         }
"""


subject = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#subject')
predicate = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate')
obj = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#object')
type_ = rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
map_ = {subject: "subject", predicate: "predicate", obj: "object", type_: "type"}

G = nx.MultiDiGraph()
supers_added = []
all_ns = [n for n in g.namespace_manager.namespaces()]
print(all_ns)
print("DOING QUERY")
r = g.query(query)
print("QUERY DONE")
i = 0
spo_counter = 0

added = defaultdict(int)
features_added = []
for row in r:
    print(f"HANDLING ROW {i}")
    synset = row.synset
    sub = row.sub
    pred = row.pred
    ob = row.obj
    supert = row.super
    G.add_node(synset)
    G.add_node(pred)
    G.add_node(sub)
    if not added[(synset, sub, pred, ob)]:
        G.add_edge(synset, sub, label=f"{spo_counter}__subject", supertype=supert)
        G.add_edge(synset, pred, label=f"{spo_counter}__predicate", supertype=supert)
        G.add_edge(synset, ob, label=f"{spo_counter}__object", supertype=supert)
        added[(synset, sub, pred, ob)] = 1
    spo_counter += 1
    i += 1

query = """
select ?synset ?feature where {
            ?synset <http://nlp/resources/features#has_feature> ?feature .
            }
"""

r = g.query(query)
for row in r:
    synset = row.synset
    feature = row.feature
    G.add_node(feature)
    G.add_node(synset)
    G.add_edge(synset, feature, label="has_feature")

with open(EXTENDED_GRAPH_PATH, "wb") as f:
    pickle.dump(G, f)
