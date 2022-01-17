from solve import *
from tqdm import tqdm

def wordsLeft(wordArr0=None, guesses=['alien', 'torus']):
    if wordArr0 is None:
        wordArr0 = load_arr(length=5)
    
    cnts = [len(wordArr0)] * len(wordArr0)
    for i, base_word in tqdm(enumerate(wordArr0), total=len(wordArr0)):
        wordArr = wordArr0
        for guess in guesses:
            fs = FilterSet()
            res = compare(base_word, guess)
            fs.update(filtersFromRes(res, guess))
            wordArr = fs.applyAll(wordArr)
        cnts[i] = len(wordArr)

    return wordArr0, cnts

