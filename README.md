# wordle-solver

This is a solver for the popular game wordle at https://www.powerlanguage.co.uk/wordle/.

The solver loads in a list of words from data/length5.txt (other files in data correspond to different length words), and then tries to guess the wordle word,
progressively filtering the word list based on information from the guesses.

To use the solver, change to the repo root and call it from the cmd line.
Example CLI demonstration:

```
# Run the base solver with no arguments (this loads up the wordle website, submits guesses, and outputs the final word if it can be found within the 6 guesses)
akshayyeluri@Akshays-MacBook-Pro-3:~/code/wordle$ python solve.py
Final word: shire

# Run the solver changing the logging level and using a particular guess_func
akshayyeluri@Akshays-MacBook-Pro-3:~/code/wordle$ python solve.py -l INFO --guess_func minOptionGuesser
[2022-01-17 18:27:01,768 | root | INFO]: Guess number: 0
[2022-01-17 18:27:01,768 | root | INFO]: Guessed alien, result was [<Res.ABSENT: 0>, <Res.ABSENT: 0>, <Res.CORRECT: 2>, <Res.PRESENT: 1>, <Res.ABSENT: 0>]
[2022-01-17 18:27:01,768 | root | INFO]: 128 words left.
[2022-01-17 18:27:04,546 | root | INFO]: Guess number: 1
[2022-01-17 18:27:04,547 | root | INFO]: Guessed torus, result was [<Res.ABSENT: 0>, <Res.ABSENT: 0>, <Res.PRESENT: 1>, <Res.ABSENT: 0>, <Res.PRESENT: 1>]
[2022-01-17 18:27:04,547 | root | INFO]: 8 words left.
[2022-01-17 18:27:07,844 | root | INFO]: Guess number: 2
[2022-01-17 18:27:07,844 | root | INFO]: Guessed brise, result was [<Res.ABSENT: 0>, <Res.PRESENT: 1>, <Res.CORRECT: 2>, <Res.PRESENT: 1>, <Res.CORRECT: 2>]
[2022-01-17 18:27:07,844 | root | INFO]: 3 words left.
[2022-01-17 18:27:10,804 | root | INFO]: Guess number: 3
[2022-01-17 18:27:10,804 | root | INFO]: Guessed shire, result was [<Res.CORRECT: 2>, <Res.CORRECT: 2>, <Res.CORRECT: 2>, <Res.CORRECT: 2>, <Res.CORRECT: 2>]
[2022-01-17 18:27:10,804 | root | INFO]: 1 words left.
Final word: shire

# Run the solver not using the web interface (manually entering results)
akshayyeluri@Akshays-MacBook-Pro-3:~/code/wordle$ python solve.py --guess_func randomGuesser --seed 32 --no_use_web
The solver has chosen guess: swizz
Please enter the results of guess as 5 space separated integers with 2=CORRECT, 0=ABSENT, 1=PRESENT (and 3 for broken tiles): 2 0 2 0 0
The solver has chosen guess: shits
Please enter the results of guess as 5 space separated integers with 2=CORRECT, 0=ABSENT, 1=PRESENT (and 3 for broken tiles): 2 2 2 0 0
The solver has chosen guess: shily
Please enter the results of guess as 5 space separated integers with 2=CORRECT, 0=ABSENT, 1=PRESENT (and 3 for broken tiles): 2 2 2 0 0
The solver has chosen guess: shirr
Please enter the results of guess as 5 space separated integers with 2=CORRECT, 0=ABSENT, 1=PRESENT (and 3 for broken tiles): 2 2 2 2 0
The solver has chosen guess: shire

Please enter the results of guess as 5 space separated integers with 2=CORRECT, 0=ABSENT, 1=PRESENT (and 3 for broken tiles): 2 2 2 2 2
Final word: shire
```

Use -h on command line to see other options

## Installing
Outside of python builtins, requires numpy, selenium, webdriver_manager (pip or conda install those)

## Files
* solve.py: The main logic of the program, runs a solver taking various command line arguments and outputs the final word
* filt.py: Code for filtering logic, where information from wordle guesses is used to filter the list of possible words to just those that are valid
* web_interface.py: Defines a web interface for interacting with the wordle website, submitting guesses, and retrieving the results of those guesses
* res.py: Encodes tokens representing the three possible results wordle gives (CORRECT, ABSENT, PRESENT), as well as logic that generates filters
  from a guess and its result
* guess.py: The heart of the solving logic, defines various "guess_funcs" that produce a guess from a list of possible options
* data/: A directory with the full scrabble dictionary, as well as separate files for each length word in the dictionary

## Guess funcs and how to test
Guess functions are the heart of the solving logic, they represent different algorithms for taking a list of words and selecting an option to guess. 
The guess functions are defined in guess.py, and are passed as parameters to the Solver class constructor (in solve.py). 

To test guess functions, the trial function defined in solve.py is very useful. This function essentially picks a random word and runs a solver, returning True/False 
depending on if the solver guesses the word or not. One can also pass the stopShort = True parameter to instead get the number of options left before the last guess.

Example:

```
akshayyeluri@Akshays-MacBook-Pro-3:~/code/wordle$ ipython
Python 3.8.3 | packaged by conda-forge | (default, Jun  1 2020, 17:21:09)
Type 'copyright', 'credits' or 'license' for more information
IPython 7.17.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: from solve import trial; from guess import scrabbleGuesser, randomGuesser

In [2]: import numpy as np

In [3]: np.mean([trial(guess_func=scrabbleGuesser) for _ in range(1000)]) # Empirical probability of solving
Out[3]: 0.884

In [4]: np.mean([trial(guess_func=randomGuesser) for _ in range(1000)]) # Empirical probability of solving
Out[4]: 0.858

In [5]: np.mean([trial(guess_func=scrabbleGuesser, stopShort=True) for _ in range(1000)]) # Average number of words left before last guess
Out[5]: 1.576

In [6]: np.mean([trial(guess_func=randomGuesser, stopShort=True) for _ in range(1000)]) # Average number of words left before last guess
Out[6]: 2.219
```


