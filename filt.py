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
    def __init__(self, letter):
        assert (isinstance(letter, str) and len(letter) == 1)
        letter = letter.lower()
        self.letter = letter
    def __eq__(self, other):
        return self.letter == other.letter
    def __hash__(self):
        return hash(self.letter)
    def __repr__(self):
        return type(self).__name__ + f"({self.letter})"

class NoLetter(Filter):
    def __call__(self, wordArr):
        return (wordArr != self.letter).all(axis=1)

class HasLetter(Filter):
    def __call__(self, wordArr):
        return (wordArr == self.letter).any(axis=1)

class HasLetterInPlace(Filter):
    def __init__(self, letter, idx):
        super(HasLetterInPlace, self).__init__(letter)
        self.idx = idx
    def __call__(self, wordArr):
        return (wordArr[:, self.idx] == self.letter)
    def __eq__(self, other):
        return self.letter == other.letter and self.idx == other.idx
    def __hash__(self):
        return hash((self.letter, self.idx))
    def __repr__(self):
        return type(self).__name__ + f"({self.letter}, {self.idx})"

class FilterSet(set):
    def cleanUp(self):
        has_letters = set([filt.letter for filt in self 
                           if isinstance(filt, (HasLetter, HasLetterInPlace))])
        bad_no_filts = [filt for filt in self if 
                        isinstance(filt, NoLetter) and filt.letter in has_letters]
        for filt in bad_no_filts:
            self.remove(filt)

    def applyAll(self, wordArr):
        import pdb; pdb.set_trace()
        self.cleanUp()
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

