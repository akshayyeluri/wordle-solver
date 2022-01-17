#!/Users/akshayyeluri/anaconda3/bin/python
import os
import numpy as np
import logging
from argparse import ArgumentParser
from web_interface import WebInterface, BIG_SLEEP
from filt import *
from enum import Enum
import time
from pprint import pprint
from tqdm import tqdm
import itertools

DATA_ROOT = "/Users/akshayyeluri/code/sandbox/wordle"
OUT_FORMAT = "length{}.txt"
MAX_WEB_RETRIEVE_RETRIES = 3

def load_arr(length, root=DATA_ROOT, out_format=OUT_FORMAT):
    """ Load a wordArr """
    with open(os.path.join(root, out_format.format(length)), 'r') as f:
        wordArr = [l.strip() for l in f.readlines()]
    return wordArr


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

# Only the following are reasonable results the web should give, others
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


############################################################
# Guess funcs (funcs that take a wordArr and return a word)
############################################################

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

def randomGuess(wordArr, **kw):
    """ Choose a random word in wordArr as the guess """
    return wordArr[np.random.choice(len(wordArr))]


def interactiveGuess(wordArr, **kw):
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
def scrabbleGuess(wordsArr, fs=None, guess_num=0,
                  info_already_penalty=[1/3, 1/3, 1/3, 1/3, 1, 1],
                  **kw):
    letter_info = set([filt.letter for filt in fs])
    info_penalty = info_already_penalty[guess_num]

    def word_scorer(word):
        lets = sorted(set(word.upper()))
        terms = [COMMONALITY_METRIC(letter) for letter in lets]
        penalties = [info_penalty if letter in letter_info else 1 for letter in lets]
        return sum([t * p for t,p in zip(terms, penalties)])

    return max(wordsArr, key=word_scorer)


@hardCodeGuess(number2GuessMap={ 0: "alien", 1: "torus"})
def minOptionGuess(wordArr, fs=None, do_max_not_avg=False, verbose=False, **kw):
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


############################################################
# Submit funcs (funcs that take a guess, submit it,
# and return the result as a list of Res values)
############################################################

def interactiveSubmit(guess):
    """
    A submit func that essentially waits for user input.
    It tells you the guess, and then you, the user, tells it
    the result
    """
    print(f"The solver has chosen guess: {''.join(guess)}")
    option_str = ', '.join([str(tok.value) + "=" + tok.name for tok in VALID_RES])
    res = input("Please enter the results of guess as 5 space separated integers "
                f"with {option_str} (and {Res.TBD.value} for broken tiles): ")
    res = [Res(int(el)) for el in res.split()]
    return res


def compare(known, guess):
    """
    Not quite a submit func, but by specifying a known word, this
    will serve as a submit func, that just submits by comparing the
    guess to the known
    """
    guess, known = np.char.array(list(guess)), np.char.array(list(known))
    res = np.where(np.isin(guess, known), Res.PRESENT, Res.ABSENT)
    res[guess == known] = Res.CORRECT

    # Sometimes, e.g. word is curve, guess=kurre, we get too many PRESENTs,
    # because the first r matches, and the second says present.
    # We want to rectify these
    for letter in known:
        cnt = (known == letter).sum()
        present_inds = [idx for idx,(g,token) in enumerate(zip(guess, res)) 
                            if (g == letter and token == Res.PRESENT)]
        correct_inds = [idx for idx,(g,token) in enumerate(zip(guess, res)) 
                            if (g == letter and token == Res.CORRECT)]

        mistaken_present = (len(present_inds) + len(correct_inds)) - cnt
        if mistaken_present == 0:
            continue

        for idx in present_inds[-mistaken_present:]:
            res[idx] = Res.ABSENT

    return list(res)


############################################################
# Stuff just for testing
############################################################

# TODO: document
# TODO: words not in wordlst handling
def trial(word=None, seed=None, nGuess = 6, length=5, stopShort=True, guess_func=None, debugger=False, **kw):
    """
    If stopShort is True, return the number of options before the last guess
    If stopShort is False, return whether or not we get the word ultimately (boolean)
    """
    # seed trials for consistency, maybe?
    if seed:
        np.random.seed(seed)

    guesses = nGuess - 1 if stopShort else nGuess
    length = len(word) if word else length
    guess_func = guess_func if guess_func else randomGuess

    slv = Solver(guess_func=guess_func, length=length, guesses=guesses,
                 uses_web_interface=False)

    if not word:
        idx = np.random.choice(len(slv.wordArr0))
        word = slv.wordArr0[idx]

    slv.submitter = lambda guess: compare(word, guess)

    if stopShort:
        wordArr = slv.run(getOptionsLeft=True, debugger=debugger, **kw)
        return len(wordArr)
    else:
        slv.run(debugger=debugger, **kw)
        return slv.final_word is not None


############################################################
# The Machinery for actually running
############################################################

class Solver:

    def __init__(self,
                 submit_func=None,
                 guess_func=interactiveGuess,
                 uses_web_interface=True,
                 length=5, guesses=6):

        self.length = length
        self.guesses = guesses

        # If there is a web interface, use the length and guesses from that
        # instead
        self.wi = None
        if uses_web_interface:
            self.wi = WebInterface()
            self.length = self.wi.length
            self.guesses = self.wi.guesses

        # Use the given submitter, if one exists, otherwise
        # assume we're using the web submitter
        if submit_func:
            self.submitter = submit_func
        else:
            self.submitter = self.submit_web

        # Use whatever guesser we're given
        self.guesser = guess_func

        self.wordArr0 = load_arr(self.length)

        self.final_word = None


    def run(self, seed=None, getOptionsLeft=False, debugger=False, **kw):
        # Some guess funcs (e.g. randomGuess) have randomness, so
        # seed the rng for consistency
        if seed:
            np.random.seed(seed)

        fs = FilterSet()
        wordArr = self.wordArr0
        guesses, resses = [], []

        for guess_num in range(self.guesses):
            if debugger:
                import pdb; pdb.set_trace()

            while True:
                # Get a guess and submit it
                guess = self.guesser(wordArr, fs=fs, guess_num=guess_num, **kw)
                res = self.submitter(guess)

                # TODO: remove numpy
                if all([result in VALID_RES for result in res]):
                    guesses.append(guess)
                    resses.append(res)
                    break

                # if bad, remove from wordArr, call submitter with clear=True,
                # and logging.warn it, then try again
                else:
                    logging.warn(f"{''.join(guess)} is not in wordle, please remove from corpus.")
                    if self.wi is not None:
                        self.wi.clearGuess()
                    if guess in wordArr:
                        wordArr.remove(guess)

            # filter the words list using the new info we learned
            fs.update(filtersFromRes(resses[-1], guesses[-1]))
            wordArr = fs.applyAll(wordArr)

            # If we've succeeded, save the final word and leave
            if all([result == Res.CORRECT for result in resses[-1]]):
                self.final_word = ''.join(guesses[-1])
                break

        if self.wi is not None:
            self.wi.shutDown()
        return self.final_word if not getOptionsLeft else wordArr



    def submit_web(self, guess):
        """
        Submits using the web interface.
        """
        self.wi.submit_guess(guess)
        # Keep trying till the values all resolve
        for _ in range(MAX_WEB_RETRIEVE_RETRIES):
            # Sleep to make sure we don't go too fast
            time.sleep(BIG_SLEEP)
            res = self.wi.retrieve_res()
            res = [Res[value.upper()] for value in res]
            # we finished getting the whole word
            if all([r in VALID_RES for r in res]):
                return res
        return res



# TODO: Think through how this stuff actually works lol
def getArgs():
    p = ArgumentParser(description="Solve wordle")
    # TODO: Implement this
    #p.add_argument('--length', default=5, type=int,
    #        help='Length of the word to guess')
    #p.add_argument('--guesses', default=6, type=int,
    #        help='Number of guesses to find the word')
    p.add_argument('-l', '--log', default='WARNING',
            help='Log level, one of [DEBUG, INFO, WARNING, ERROR, CRITICAL')
    return p.parse_args()


def main():
    args = getArgs()
    logging.basicConfig(level=getattr(logging, args.log),
                        format='[%(asctime)s | %(name)s | %(levelname)s]: %(message)s')


if __name__ == "__main__":
    main()


