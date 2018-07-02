import time

import requests
import json

from requests import HTTPError
from urllib3.exceptions import MaxRetryError, NewConnectionError

"""
pairs = [
    {'t1': 'house', 't2': 'beer'},
    {'t1': 'car', 't2': 'engine'}]

data = {'corpus': 'googlenews',
        'model': 'W2V',
        'language': 'EN',
        'scoreFunction': 'COSINE', 'pairs': pairs}

headers = {
    'content-type': "application/json"
}

res = requests.post("http://localhost:8916/relatedness", data=json.dumps(data), headers=headers)
res.raise_for_status()
print(res.json())
"""

def check_relatedness(t1, t2):
    if "#" in t1:
        t1 = " ".join(t1.split("#")[1].split("_"))
    pairs = [
        {"t1": t1, "t2": t2}
    ]
    data = {'corpus': 'googlenews',
            'model': 'W2V',
            'language': 'EN',
            'scoreFunction': 'COSINE', 'pairs': pairs}

    headers = {
        'content-type': "application/json"
    }
    res = requests.post("http://localhost:8916/relatedness", data=json.dumps(data), headers=headers)
    res.raise_for_status()
    j = res.json()
    return j["pairs"][0]["score"]


def check_relatedness_pairs(pairs):
    p = []
    for t1, t2 in pairs:
        p.append({"t1": t1, "t2": t2})
    data = {'corpus': 'googlenews',
            'model': 'W2V',
            'language': 'EN',
            'scoreFunction': 'COSINE', 'pairs': p}

    headers = {
        'content-type': "application/json"
    }
    f = False
    try:
        res = requests.post("http://localhost:8916/relatedness", data=json.dumps(data), headers=headers)
    except (ConnectionError, requests.exceptions.ConnectionError, MaxRetryError, NewConnectionError):
        time.sleep(5)
        print("---ERROR IN INDRA, TRYING AGAIN---")
        res = requests.post("http://localhost:8916/relatedness", data=json.dumps(data), headers=headers)
        if f:
            print("---BLANK---")
            return {}
    try:
        res.raise_for_status()
    except HTTPError:
        return {}  # some sort of problem, go
    try:
        j = res.json()["pairs"]
    except KeyError:
        j = {}
    dd = {}
    for d in j:
        t1 = d["t1"]
        t2 = d["t2"]
        dd[(t1, t2)] = d["score"]
    return dd


# print(check_relatedness("picture", "for taking photographs"))