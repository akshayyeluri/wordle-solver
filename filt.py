"""
A module defining the filtering logic for wordle.

This module has instances of a Filter class that represent filters on a list
of words imposed by the information gleaned from wordle guesses. E.g. if
the word guessed is 'alien', and we learn 'a' does not occur in the actual word,
this can be represented by an UpperBound('a', 0) filter, while if 'l' does occur
in the same position in the actual word, this is represented by a HasLetterAt('l', 1)
filter. 

There is also a FilterSet class, a subclass of pythons builtin set, with
handy methods for applying all the filters in the set to a list of words / 
summarizing the info from the filters in the set.
"""
import numpy as np
from functools import reduce
from collections import defaultdict

# All the filters / the filtersets we wish to use in the solver
__all__ = ['LowerBound', 'UpperBound', 'HasLetterAt', 'NoLetterAt', 'FilterSet']

class Filter:
    """
    Superclass for filters, all subclasses must implement the call method
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
    """ A filter specifying a letter (self.letter) occurs >= a number (self.num) of times """
    def __call__(self, wordArr):
        return (wordArr == self.letter).sum(axis=1) >= self.num

class UpperBound(Filter):
    """ A filter specifying a letter (self.letter) occurs <= a number (self.num) of times """
    def __call__(self, wordArr):
        return (wordArr == self.letter).sum(axis=1) <= self.num

class HasLetterAt(Filter):
    """ A filter specifying a letter (self.letter) is at a location (self.num) """
    def __call__(self, wordArr):
        return (wordArr[:, self.num] == self.letter)

class NoLetterAt(Filter):
    """ A filter specifying a letter (self.letter) is NOT at a location (self.num) """
    def __call__(self, wordArr):
        return (wordArr[:, self.num] != self.letter)

class FilterSet(set):
    """
    A subclass of set that defines a set of filters. Can be constructed /
    modified in the same way as a set.
    """

    def applyAll(self, wordArr):
        """
        Apply all the filters in this filter set to a list of words,
        and return the words that meet all the criteria
        """
        wordArr_np = np.char.array([list(word) for word in wordArr])
        idx = reduce(lambda x,y: x & y, [filt(wordArr_np) for filt in self], True)
        return [''.join(word) for word in wordArr_np[idx]]

    def counts_by_type(self):
        """
        Return a dictionary of how many of each type of filter
        there are in this filter set
        """
        cnts = defaultdict(int)
        for filt in self:
            cnts[type(filt).__name__] += 1
        return dict(cnts)

    def counts(self, typ):
        """
        Return the number of filters of a certain type
        """
        return self.counts_by_type()[typ]

