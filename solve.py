#!/Users/akshayyeluri/anaconda3/envs/web_bots/bin/python
from web_interface import WebInterface, BIG_SLEEP
from filt import FilterSet
from res import Res, VALID_RES, filtersFromRes
import guess

import os
import logging
from argparse import ArgumentParser
import time

import numpy as np

# Retrieve the full set of guess func options from the guess module
GUESS_FUNCS = {func_name: getattr(guess, func_name) for func_name in dir(guess)
               if func_name[-len("Guesser"):] == "Guesser"}

# The default guessing function (should be the best one)
DEFAULT_GUESS_FUNC = "scrabbleGuesser"

FNAME = "data/length{}.txt"
MAX_WEB_RETRIEVE_RETRIES = 3

def load_words(length, fname=FNAME):
    """ Load the list of words """
    with open(fname.format(length), 'r') as f:
        wordArr = [l.strip() for l in f.readlines()]
    return wordArr


############################################################
# Submit funcs (funcs that take a guess, submit it,
# and return the result as a list of Res values)
############################################################

def interactiveSubmitter(guess):
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
# Testing code (only used for evaluating how different 
# guess funcs perform really)
############################################################

def trial(word=None, seed=None, nGuess = 6, length=5, stopShort=True, guess_func=None, debugger=False, **kw):
    """
    Run a single trial where a solver tries to guess a word

    @param word: 
        The word to guess, will be randomly chosen from the solvers
        starting word list if None

    @param seed:
        A random seed to use if working with a solver that has randomness
        (also in choosing a word if word=None)

    @param nGuess:
        The number of guesses the solver gets to guess the word

    @param length:
        The length of the word to guess, meaningless if word is not None

    @param stopShort:
        Set this to True to stop one short of nGuess and return the number
        of options left, set to False to return just a boolean for
        whether the solver got the word or not

    @param guess_func:
        A particular guess_func to use from guess.py

    @param debugger:
        Set to True to stop in the solver after each guess

    @param **kw:
        Other kwargs to pass to the solver / guess_function

    @return:
        nOptionsLeft OR didSolverGuessWord, an integer / boolean respectively
        giving the number of options before the last guess / whether the solver
        got the word. Returns nOptionsLeft if stopShort = True, else 
        didSolverGuessWord.
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
# The Solver class itself
############################################################

class Solver:

    def __init__(self,
                 submit_func=None,
                 guess_func=None,
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

        # Load the words we care about
        self.wordArr0 = load_words(self.length)

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

                if all([result in VALID_RES for result in res]):
                    guesses.append(guess)
                    resses.append(res)
                    break

                # if bad, remove from wordArr, call submitter with clear=True,
                # and logging.warn it, then try again
                else:
                    logging.warning(f"{''.join(guess)} is not in wordle, please remove from corpus.")
                    if self.wi is not None:
                        self.wi.clearGuess()
                    if guess in wordArr:
                        wordArr.remove(guess)

            # filter the words list using the new info we learned
            fs.update(filtersFromRes(resses[-1], guesses[-1]))
            wordArr = fs.applyAll(wordArr)

            logging.info(f"Guess number: {guess_num}")
            logging.info(f"Guessed {guesses[-1]}, result was {resses[-1]}")
            logging.info(f"{len(wordArr)} words left.")

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


def getArgs():
    """
    Parse the arguments
    """
    p = ArgumentParser(description="Solve wordle")
    p.add_argument('--guess_func', default=DEFAULT_GUESS_FUNC,
                   help="The function to use while guessing, options are: " +
                        ", ".join(GUESS_FUNCS.keys()))
    p.add_argument('--no_use_web', action="store_true",
                   help="Don't use the web interface and instead manually enter the "
                        "results of each guess.")
    p.add_argument('--debug', action="store_true",
                   help="Pull up a debugger after every guess from the solver.")
    p.add_argument('--seed', default=42, type=int,
                   help="Random seed for nondeterministic guess functions.")
    p.add_argument('--nGuess', default=6, type=int,
                   help="Number of guesses the solver will get to find the word (only matters if no_use_web).")
    p.add_argument('--length', default=5, type=int,
                   help="Length of the words solver will be guessing (only matters if no_use_web).")
    p.add_argument('-l', '--log', default='WARNING',
            help='Log level, one of [DEBUG, INFO, WARNING, ERROR, CRITICAL')
    return p.parse_args()


def main():
    """
    Run a solver with arguments parsed from CLI
    """
    args = getArgs()
    logging.basicConfig(level=getattr(logging, args.log),
                        format='[%(asctime)s | %(name)s | %(levelname)s]: %(message)s')

    submit_func = None
    if args.no_use_web:
        submit_func = interactiveSubmitter

    guess_func = GUESS_FUNCS[DEFAULT_GUESS_FUNC]
    if args.guess_func in GUESS_FUNCS:
        guess_func = GUESS_FUNCS[args.guess_func]

    slv = Solver(submit_func=submit_func, guess_func=guess_func,
                 uses_web_interface = (not args.no_use_web),
                 length = args.length, guesses = args.nGuess)

    final_word = slv.run(seed=args.seed, debugger=args.debug, getOptionsLeft=False)
    if final_word is not None:
        print(f"Final word: {final_word}")
    else:
        print(f"Unable to solve!")


if __name__ == "__main__":
    main()


