def load_bpi():
    with open("bpi-rte.txt", "r") as f:
        content = f.read()
    pairs = content.split("\n\n")
    pairs_done = {"YES": list(), "NO": list()}
    for pair in pairs:
        try:
            text, hypothesis, entailment = pair.split("\n")
        except ValueError:
            # last pair
            text, hypothesis, entailment, _ = pair.split("\n")
        text = text.split("T: ")[1]
        hypothesis = hypothesis.split("H: ")[1]
        entailment = entailment.split("A: ")[1]
        pairs_done[entailment].append((text, hypothesis))
    return pairs_done
