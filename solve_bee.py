"""
A simple spelling bee solver to demonstrate the versatility of filter sets
and stuff.
"""
import os
import itertools
from filt import *
from string import ascii_lowercase
from collections import defaultdict

DATA_ROOT = "/Users/akshayyeluri/code/sandbox/wordle"

def solve(midLetter, letters, wordArr=None, minLength=4):
    letters = [l.lower() for l in letters]
    midLetter = midLetter.lower()

    s = set(letters + [midLetter])
    invalid = set(ascii_lowercase) - s

    fs = FilterSet([UpperBound(l, 0) for l in invalid])
    fs.add(LowerBound(midLetter, 1))

    if wordArr is None:
        wordArr = load_arr()

    # Have to aggregate by length
    length2words = defaultdict(list)
    for word in wordArr:
        length2words[len(word)].append(word)
    
    # solution
    length2ans = {k:fs.applyAll(v) for k,v in length2words.items()}
    
    words = list(itertools.chain(*[v for k,v in length2ans.items() if k >= minLength]))
    return words



def load_arr(root=DATA_ROOT, name="full_dict.txt"):
    """ Load a wordArr """
    with open(os.path.join(root, name), 'r') as f:
        wordArr = [l.strip().lower() for l in f.readlines()]
    return wordArr

