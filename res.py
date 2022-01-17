from enum import Enum
from collections import defaultdict
from filt import UpperBound, LowerBound, HasLetterAt, NoLetterAt, FilterSet

import numpy as np

class Res(Enum):
    """
    Encodes possible results for each letter in a guess,
    submit_funcs return a list of these
    """
    CORRECT = 2
    PRESENT = 1
    ABSENT = 0
    TBD = 3
    EMPTY = 4

# Only the following are reasonable results the web interface should give, others
# mean something went wrong with the web interface (likely need to
# make the web interface sleep longer because it moved too fast for the website
# to keep up)
VALID_RES = [Res.CORRECT, Res.ABSENT, Res.PRESENT]

def filtersFromRes(res, guess):
    """
    Given a res from a submit_func, and a guess from a guess_func, this
    compares the two and returns a filterset according to how the res did.
    """
    lower_bounds = defaultdict(int)
    upper_bounds = defaultdict(int)
    must_not_be = defaultdict(set)
    must_be = defaultdict(set)

    # Have to go through the matches first, then the presents, then absents
    inds = sorted(range(len(res)), key=lambda x: res[x].value, reverse=True)
    res = np.array(res)[inds]
    guess = np.array(list(guess))[inds]

    for i, (v,c) in enumerate(zip(res, guess)):
        idx = inds[i]
        if v == Res.CORRECT:
            lower_bounds[c] += 1
            must_be[c].add(idx)
        elif v == Res.PRESENT:
            lower_bounds[c] += 1
            must_not_be[c].add(idx)
        elif v == Res.ABSENT:
            upper_bounds[c] = lower_bounds.get(c,0)
            must_not_be[c].add(idx)

    fs = FilterSet([LowerBound(c,v) for c,v in lower_bounds.items()])
    fs.update([UpperBound(c,v) for c,v, in upper_bounds.items()])
    fs.update([HasLetterAt(c,idx) for c,idxes in must_be.items() for idx in idxes])
    fs.update([NoLetterAt(c,idx) for c,idxes in must_not_be.items() 
                               for idx in idxes if lower_bounds[c] > 0])
    return fs

