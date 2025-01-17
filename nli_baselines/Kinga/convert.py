import gensim
import json
import spacy

model = gensim.models.KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True, limit=100000)
nlp = spacy.load('en')
special_characters = [',', '.', '?', '!', ':', ';', '-', '(', ')']


class Information:
    def __init__(self, sentence1, sentence2, label):
        self.sentence1 = sentence1
        self.sentence2 = sentence2
        self.label = label


def get_information(line):
    loaded = json.loads(line)
    label = 0
    if loaded["gold_label"] == "contradiction":
        label = -1
    elif loaded["gold_label"] == "entailment":
        label = 1
    return Information(loaded["sentence1"], loaded["sentence2"], label)


def analyse_line(line):
    sentence = get_information(line)
    root1 = vectorise(sentence.sentence1)
    root2 = vectorise(sentence.sentence2)
    similarity_per_root = []
    root_pairs = [(r1, r2) for r1 in root1 for r2 in root2]
    for root_pair in root_pairs:
        try:
            similarity = {"root": model.similarity(root_pair[0], root_pair[1])}
            child_similarity = []
            for child1 in root1[root_pair[0]]:
                best_child2 = 0.0
                for child2 in root2[root_pair[1]]:
                    if child1 == child2:
                        best_child2 = 1.0
                    elif child1.startswith("-PRON-") or child2.startswith("-PRON-"):
                        continue
                    else:
                        try:
                            child_sim = model.similarity(child1, child2)
                            if best_child2 < child_sim:
                                best_child2 = child_sim
                        except KeyError:
                            continue
                    child_similarity.append(best_child2)
                similarity["children"] = child_similarity
            similarity_per_root.append(similarity)
        except KeyError:
            return None
    return {"label": sentence.label, "relations": similarity_per_root}


def vectorise(sentence):
    roots = {}
    root = ""
    for token in nlp(sentence):
        children = []
        if token.dep_ == "ROOT":
            root = token.lemma_
            children0 = [child for child in token.children if child.text not in special_characters]

            for child in children0:
                if child.lemma_ == "-PRON-":
                    children.append("-PRON-"+child.text.lower())
                else:
                    children.append(child.lemma_)
            roots[root] = children
    return roots


def main():
    with open('multinli_1.0_train.jsonl', 'r') as jsonl:
        line = jsonl.readline()
        i = 0
        label_and_similarity = {}
        while line is not None and line != "":
            label_and_similarity["sentence_pair"+str(i)] = analyse_line(line)
            i += 1
            line = jsonl.readline()

    with open('root-children.json', 'w') as jsonl_out:
        json.dump(label_and_similarity, jsonl_out)


if __name__ == '__main__':
    main()