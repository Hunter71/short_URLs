import random
import string

import sqids


class CharChainsGenerator:
    """
    Allows to reversibly convert given integer into pseudo-random chain of characters.
    The generated string would look like a random one, but in fact it would be built in the deterministic way,
    allowing reverse decoding of that string into the original integer back and forth.

    The [Sqids](https://sqids.org/) tool would be used to generate a pseudo-random string from given int.

    Under the hood, it would use a bijective function converting the given integer of base 10
    into the number with a base of `len(alphabet)`, where alphabet is the chain of the allowed
    characters in a specific order.
    Then every digit from the converted number is replaced with the alphabet's character located
    under the index corresponding to the digit.

    Let's consider example conversion of the `100` number, when the alphabet's size is 64:

        # define alphabet for the conversion algorithm
        alphabet = string.ascii_letters + string.digits + "_-"

        # find the BASE 64 representation of 100 (10)
        # 100(10) = 1 * 64 ^ 1 + 36 * 64 ^ 0 = [1, 36](64)

        # map digits from BASE 64 number representation into alphabet's characters
        new_chain = alphabet[1] + alphabet[36]
        print(new_chain)  # bK

    In the same time, the reverse conversion would be even simpler:

        # find out BASE 64 substitute of the new_chain
        digits_64 = [alphabet.index(ch) for ch in new_chain]
        print(digits_64)  # [1, 36]

        # convert BASE 64 number into BASE 10
        # [1, 36](64) = 100(10)

    There is a very insightful discussion of how to create the URL shortener
    allowing for the reversible conversion on [Stack Overflow](https://stackoverflow.com/questions/742013).
    Especially [this](https://stackoverflow.com/a/742047/3081328) answer put a great, broader explanation
    on that topic.

    Although the algorithm seems to be pretty simple, the Sqids makes it a little bit more sophisticated
    by excluding vulgarisms, allowing to define minimal length of the generated characters chains
    or ensuring the chains created from consecutive numbers are pretty distant from each other, like:

        Sqids(alphabet).encode([1221])  # "0tY"
        Sqids(alphabet).encode([1222])  # "x_r"
        Sqids(alphabet).encode([1223])  # "y0V"

    To learn more benefits from using Sqids, please see the __Features__ section on [Sqids site](https://sqids.org/).

    The seed would be used to shuffle the Alphabet characters in a way
    that allows the shuffled string to be recreated in an identical order.
    """

    def __init__(self, alphabet: str = string.ascii_letters, seed: int | None = None, min_len: int = 4):
        alphabet = self._prepare_alphabet(alphabet, seed)

        self.sqids = sqids.Sqids(alphabet=alphabet, min_length=min_len)
        self.__alphabet = alphabet

    @property
    def alphabet(self) -> str:
        """
        Defining the alphabet of allowed characters in a specific order.
        Alphabet would be used as a base dictionary for the character chains generation.
        """
        return self.__alphabet

    def encode(self, n: int) -> str:
        """
        Generate a pseudo-random characters chain from the given integer in a deterministic way,
        allowing to reverse conversion of the generated string into the original number back and forth.
        """
        return self.sqids.encode([n])

    def decode(self, chain: str) -> int:
        """Convert a given characters chain back to the integer from which it was originally generated."""
        if len(chain) < self.sqids.min_length:
            raise ValueError(f"Given characters chain '{chain}' is too short, min length: {self.sqids.min_length}")

        if not (result := self.sqids.decode(chain)):
            raise ValueError(f"Given characters chain '{chain}' is incorrect and can not be converted!")

        return result[0]

    @staticmethod
    def _prepare_alphabet(alphabet: str, seed: int | None) -> str:
        new_alphabet = list(alphabet)
        if seed is not None:
            # using seed would allow to shuffle the order of characters in the alphabet
            # in the deterministic way, allowing to regenerate the shuffled sequence every time it's needed
            random.seed(seed)
            # Shuffling the alphabet would make it harder to determine the correct characters order by 3rd parties,
            # comparing to the usage of the natural/alphabetical order.
            # In consequence, it would be orders of magnitude harder (although technically still possible)
            # to guess the sequence of character chains generated from the consecutive integers,
            # which is a common goal of the brute force attacks against such APIs.
            #
            # All the above assumes the seed is secret and the API code is private, and inaccessible to API clients.
            random.shuffle(new_alphabet)

        return "".join(new_alphabet)
