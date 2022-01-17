"""
A module defining the web interface for the solver.

The web interface is the code that loads up the wordle website, submits guesses
to the site, and fetches the results of the guesses.

NOTE: Need to pip/conda install selenium and webdriver_manager to use this,
will also download a web driver for chrome to use properly
"""
import logging
import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

URL = 'https://www.powerlanguage.co.uk/wordle/'
WEBDRIVER_PATH = "/Users/akshayyeluri/.wdm/drivers/chromedriver/mac64/97.0.4692.71/chromedriver"
BIG_SLEEP  = 1   # Big sleeps are to be used for waiting for things like popups
SMOL_SLEEP = 0.1 # Smol sleeps are to be used for things like entering letters

class WebInterface:
    """
    An Interface for interacting with the website, capable of submitting guesses
    and telling you how those guesses did.
    """

    def __init__(self, url=URL):
        self.url = url

        self._browser = self._getBrowser()
        self._browser.get(url)

        self._exec_js = self._browser.execute_script
        self._game = self._exec_js('return document.querySelector("body > game-app")'
                                   '.shadowRoot.querySelector("#game")')

        self._grid = self._getGrid()
        self._keys = self._getKeyboard()
        self._num_guessed = 0

        self.guesses = len(self._grid)
        self.length = len(self._grid[0])

        # Sleep a little, then close the Popup
        time.sleep(BIG_SLEEP)
        self.tryClosePopup()


    def submit_guess(self, guess):
        """
        Submit a guess to the website, a guess being a word
        (either string or array-like) with exactly self.length
        characters.
        """
        if not isinstance(guess, str):
            guess = ''.join(guess)

        assert (len(guess) == self.length) and (isinstance(guess, str))

        guess = guess.upper()
        for char in guess:
            self._keys[char].click()
            # Sleep for a little to make sure we don't break
            time.sleep(SMOL_SLEEP)

        self._keys['ENTER'].click()

        self._num_guessed += 1

        if self._num_guessed == self.guesses:
            # Wait a little and then close the popup
            while not (self.tryClosePopup()):
                time.sleep(BIG_SLEEP)


    def retrieve_res(self):
        """
        Retrieve the results of the last guess,
        returned as list of length self.length,
        with one of ('correct', 'absent', 'present', 'empty', 'tbd')
        as each element in the list.
        """
        assert (self._num_guessed > 0)
        row_idx = self._num_guessed - 1
        res = [tile.get_attribute('data-state') for tile in self._grid[row_idx]]
        return res


    def _getBrowser(self, webdriver_path=WEBDRIVER_PATH):
        """
        Retrieve the browser, potentially downloading the right driver if necessary
        """
        try:
            browser = webdriver.Chrome(webdriver_path)
        except:
            # Try again after reinstall
            webdriver_path = ChromeDriverManager().install()
            logging.warn(f"Installing new webdriver to {webdriver_path}")
            browser = webdriver.Chrome(webdriver_path)

        # Get the website
        return browser


    def tryClosePopup(self):
        """
        An annoying popup sometimes appears in the game, especially when starting /
        after the game ends, and this method just closes the popup.
        """
        try:
            game_box = self._exec_js('return arguments[0].querySelector("game-modal")'
                                     '.shadowRoot.querySelector("div")', self._game)
            close_box = game_box.find_element_by_tag_name('game-icon')
            close_box.click()
            return True
        except:
            logging.info("No box to close!")
            return False


    def _getKeyboard(self):
        """
        Return the keyboard, where letters are entered.
        Returns a dictionary mapping characters to the buttons on the game's
        keyboard for those characters.

        e.g. if keys = self._getKeyboard(), then
        keys['A'].click() will enter an A into the game

        Special keys include 'ENTER' and 'DELETE' for submitting a full guess/
        backspacing respectively (so keys['ENTER'].click() submits a guess)
        """
        keyboard = self._exec_js('return arguments[0].querySelector("game-keyboard")'
                                 '.shadowRoot.querySelector("#keyboard")', self._game)
        keys = {but.text: but for but in keyboard.find_elements_by_tag_name('button')}
        keys['DELETE'] = keys.pop('')
        return keys


    def _getGrid(self):
        """
        Fetch the grid of tiles where the letters go (for seeing how the guesses went)
        Returns a list of lists, where each element in the inner lists
        is a tile html object.
        """
        board = self._game.find_element_by_id('board')
        rows = [self._exec_js('return arguments[0].shadowRoot.querySelector("div")', row)
                for row in board.find_elements_by_tag_name('game-row')]
        grid = []
        for row in rows:
            kids = [self._exec_js('return arguments[0].shadowRoot.querySelector("div")', kid)
                    for kid in row.find_elements_by_tag_name('game-tile')]
            grid.append(kids)

        return grid

    def clearGuess(self):
        self._num_guessed -= 1
        for _ in range(self.length):
            time.sleep(SMOL_SLEEP)
            self._keys['DELETE'].click()


    def shutDown(self):
        """
        Shut down this web interface.
        """
        time.sleep(BIG_SLEEP)
        self._browser.close()

