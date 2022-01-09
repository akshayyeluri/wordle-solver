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
    fs = FilterSet([(HasLetterInPlace(c, i) if v == Res.CORRECT else 
                    (HasLetter(c) if v == Res.PRESENT else NoLetter(c)))
                    for i, (v,c) in enumerate(zip(res, guess))])
    return fs


############################################################
# Guess funcs (funcs that take a wordArr and return a word)
############################################################
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
    return list(res)


############################################################
# Stuff just for testing
############################################################

# TODO: document
# TODO: words not in wordlst handling
def trial(word=None, seed=None, nGuess = 6, length=5, stopShort=True, guess_func=None):
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
    return len(slv.run(getOptionsLeft=True))


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


    def run(self, seed=None, getOptionsLeft=False):
        # Some guess funcs (e.g. randomGuess) have randomness, so
        # seed the rng for consistency
        if seed:
            np.random.seed(seed)

        fs = FilterSet()
        wordArr = self.wordArr0
        for guess_num in range(self.guesses):
            #import pdb; pdb.set_trace()

            while True:
                # Get a guess and submit it
                guess = self.guesser(wordArr, fs=fs, guess_num=guess_num)
                res = self.submitter(guess)

                # TODO: remove numpy
                if all([result in VALID_RES for result in res]):
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
            fs.update(filtersFromRes(res, guess))
            wordArr = fs.applyAll(wordArr)

            # If we've succeeded, save the final word and leave
            if all([result == Res.CORRECT for result in res]):
                self.final_word = ''.join(guess)
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


