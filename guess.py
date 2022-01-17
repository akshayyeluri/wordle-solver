"""
A module defining the various options for guess_funcs

A guess_func is any function that takes a wordArr
(a list of words to choose from) and returns a specific word 
from the list of options. This is the heart of the solver,
and different guess_funcs will have different pros and cons.

To specify a new guess func, simply create a function that at the
very least takes a wordArr (list of strings), as well as **kw
(to capture extra keyword args), and returns a specific word
from wordArr as the guess. You can use other keyword arguments
(e.g. fs: the filterset capturing info from previous guesses,
guess_num: which guess we're on, verbose: whether to print 
a tqdm progress bar or not). To use other keyword arguments, just
specify them when creating a Solver instance.
"""
from res import VALID_RES, filtersFromRes
from filt import FilterSet

from pprint import pprint
import itertools

from tqdm import tqdm
import numpy as np

# The guess functions that the solver will import / be able to use
__all__ = ['randomGuesser', 'interactiveGuesser', 
           'scrabbleGuesser', 'minOptionGuesser']

def hardCodeGuess(number2GuessMap={}):
    """
    Decorator that hard codes a specific guess for a specific
    guess number
    """
    def decorator(guess_func):
        def wrapped(wordArr, guess_num, **kw):
            if guess_num in number2GuessMap:
                return number2GuessMap[guess_num]
            return guess_func(wordArr, guess_num=guess_num, **kw)
        return wrapped
    return decorator


def randomGuesser(wordArr, **kw):
    """ Choose a random word from the set of options as the guess """
    return wordArr[np.random.choice(len(wordArr))]


def interactiveGuesser(wordArr, **kw):
    """ Asks the user to choose a word interactively from wordArr """
    words = [''.join(word) for word in wordArr]

    print(f'There are {len(words)} options to choose from.')

    opt_in = input('Would you like to see the options? (y/n): ')
    opt_in = opt_in in ('y', 'Y', 'yes', 'Yes')
    if opt_in:
        pprint(words)

    guess = input('Enter the word you want to guess, with no spaces, '
                  f'making sure it is {len(wordArr[0])} letters long: ')

    return guess


SCRABBLE_VALS = {
    1: "AEILNORSTU",
    2: "DG",
    3: "BCMP",
    4: "FHVWY",
    5: "K",
    8: "JX",
    10: "QZ",
}

SCRABBLE_PTS = {letter:val for val,lets in SCRABBLE_VALS.items() for letter in lets}
COMMONALITY_METRIC = lambda l: max(SCRABBLE_VALS) + 1 - SCRABBLE_PTS[l]

@hardCodeGuess(number2GuessMap={ 0: "alien", 1: "torus" })
def scrabbleGuesser(wordsArr, fs=None, guess_num=0,
                    info_already_penalty=lambda g_num: 1/6 * (g_num + 1),
                    **kw):
    """
    Make guesses by choosing the word that has the highest "inverse scrabble"
    score, where the "inverse scrabble" score of a word is the word's scrabble
    score subtracted from a constant (so the lowest scrabble score words
    are more likely to be chosen).

    The intuition is that words with low scrabble scores are more common, and
    therefore likely to be better. To avoid guessing words that don't give a lot
    of new information, there's also an info_already_penalty function as a parameter
    that weights letters already seen before in computing an inverse scrabble score.
    The function takes the guess number as an argument (so for earlier guesses,
    letters already seen are weighted lower to avoid guessing words without a lot
    of new info, but this weighting disappears for higher guess numbers).
    """
    letter_info = set([filt.letter for filt in fs])
    info_penalty = info_already_penalty(guess_num)

    def word_scorer(word):
        lets = sorted(set(word.upper()))
        terms = [COMMONALITY_METRIC(letter) for letter in lets]
        penalties = [info_penalty if letter in letter_info else 1 for letter in lets]
        return sum([t * p for t,p in zip(terms, penalties)])

    return max(wordsArr, key=word_scorer)


@hardCodeGuess(number2GuessMap={ 0: "alien", 1: "torus"})
def minOptionGuesser(wordArr, fs=None, do_max_not_avg=False, verbose=False, **kw):
    """
    Make guesses by choosing the word that limits the average (or max) number
    of options after incorporating information about the word. The average
    (or max) is taken over all (3 ** word_length) 
    possible results from the guessed word.
    """
    opts = [0] * len(wordArr)
    length = len(wordArr[0])
    func = np.max if do_max_not_avg else np.mean

    iterable = enumerate(wordArr)
    if verbose:
        iterable = tqdm(iterable, total=len(wordArr))
    for i, word in iterable:
        cnts = []
        for res in itertools.product(VALID_RES, repeat=length):
            fs2 = FilterSet(fs.copy())
            fs2.update(filtersFromRes(res, word))
            cnts.append(len(fs2.applyAll(wordArr)))
        opts[i] = func(cnts)

    return wordArr[np.argmin(opts)]



