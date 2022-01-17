import numpy as np
from functools import reduce
from collections import defaultdict

# TODO:
# If word is 'banal', eg, and we guess
# annex, the first n is CORRECT, second gets ABSENT, because
# we actually have all the n's. Rethink stuff to work with this

class Filter:
    """
    Superclass, all subclasses must implement the call method
    """
    def __call__(self, wordArr):
        """
        Take a numpy array of shape (nWords, LENGTH), return
        a numpy boolean vector of shape nWords saying which words meet the filter
        """
        pass
    def __init__(self, letter, num):
        """
        Letter is the letter the filter applies to,
        num is either an idx or a count
        """
        assert (isinstance(letter, str) and len(letter) == 1)
        assert (isinstance(num, int))
        letter = letter.lower()
        self.letter = letter
        self.num = num
    def __eq__(self, other):
        return type(self) == type(other) and self.letter == other.letter and self.num == other.num
    def __hash__(self):
        return hash((self.letter, self.num))
    def __repr__(self):
        return type(self).__name__ + f"({self.letter}, {self.num})"

class LowerBound(Filter):
    def __call__(self, wordArr):
        return (wordArr == self.letter).sum(axis=1) >= self.num

class UpperBound(Filter):
    def __call__(self, wordArr):
        return (wordArr == self.letter).sum(axis=1) <= self.num

class HasLetterAt(Filter):
    def __call__(self, wordArr):
        return (wordArr[:, self.num] == self.letter)

class NoLetterAt(Filter):
    def __call__(self, wordArr):
        return (wordArr[:, self.num] != self.letter)

class FilterSet(set):
    def applyAll(self, wordArr):
        wordArr_np = np.char.array([list(word) for word in wordArr])
        idx = reduce(lambda x,y: x & y, [filt(wordArr_np) for filt in self], True)
        return [''.join(word) for word in wordArr_np[idx]]

    def counts_by_type(self):
        cnts = defaultdict(int)
        for filt in self:
            cnts[type(filt).__name__] += 1
        return dict(cnts)

    def counts(self, typ):
        return self.counts_by_type()[typ]

