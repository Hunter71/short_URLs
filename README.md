# Short URLs
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

Application allowing to create short replacement for the given origin URL.

## Documentation

Project's API is available on GitHub Pages: https://hunter71.github.io/short_URLs/

## Local development

### Run application

Note: Before following below steps, make sure you have properly installed [`poetry`](https://python-poetry.org/docs/#installation) package.

Installation can be performed by running below command:

    poetry install

Then running application is pretty simple. Just run below command:

    ./bin/run-server

You should see below info in the console:

    Django version 4.2.5, using settings 'short_URLs.settings'
    Starting development server at http://0.0.0.0:8000/
    Quit the server with CONTROL-C.

This means API is ready to use on localhost on the port 8000.

### Example interaction with API

Create short version of the URL with POST request

    $ curl -X POST http://localhost:8000/ -H "Content-Type: application/json" -d '{"url": "http://google.com"}'
    {"short_url":"http://localhost:8000/9gsi"}

Resolve short URL to original URL with the GET endpoint (it will simply redirect you to the original URL)

    curl http://localhost:8000/cmzi

(no visible effects of redirection, click the link to see that redirection actually works).

### Run tests

First make sure the project was installed locally as described in `Run application locally (via poetry)` section.
Then run one of below command locally to run unit or integration tests: 

    ./bin/run-tests

### Check codestyle

First make sure the project was installed locally as described in `Run application locally (via poetry)` section.
Then run below command locally to perform codestyle check: 

    ./bin/run-codestyle-check

If codestyle is ok, you should see the below final message in the console output. Otherwise, proper error will be displayed.

    👏 Good job! Codestyle is awesome 👌

### Docker-based development

Instead of installing all the dependencies locally, one can build Docker image and start API server in the Docker container:

    docker compose build

    # run tests with coverage
    docker compose up tests
    # check codestyle
    docker compose up codestyle

    # start server
    docker compose up app

## API design

### Generation of the short URL

Short URL will be generated using bijective function with the record id as an argument.
This would allow to convert the short url back into record ID, allowing to decode the short URL
into it's original URL.
Thanks to that, it does not have to be stored in the database, as it can be converted back from short URL.

Proposed approach has both pros and cons.

#### Pros

(P1) Decision to generate short URL on fly would allow to limit the columns of the URL record
stored in the database and the number of indexes. In case of storing shortened version of the URL,
this column should be indexed to optimize SELECT requests when retrieving urls from database.
With the selected approach, only primary key ID column is relevant and no other index is required.

(P2) There is no need to ensure uniqueness of the original URL. Since short URL generation based on
the record ID, it is possible to have a duplicated original URLs with different shortened versions.
This is not harmful scenario, as still all the short URLs would be unique (as record IDs have to be unique),
so they still can be unambiguously translated into the original URL.
Allowing duplicated original URLs make possible to skip expensive EXISTS check on every POST request
to create short URL.

#### Cons

(C1) Generating short URLs on fly has a single major consequence of being sensitive to the data consistency.
Every such operation, as listed below, can harm the bidirectional conversion between original and short URLs
and cause strange application behaviours, like not recognizing self-created short URLS:
 - changing record ID
 - changing CharChainsGenerator underlying alphabet
 - using different seeds for alphabet shuffling on the application (re)start
 - resetting AUTO_INCREMENT to arbitrarily selected value

Any of the above operation should be considered as potential danger to the application reliability
and consistency. Thus, if there exists an important use case to perform one of those operations,
then short URL generation design should be re-considered for change.

### Bidirectional conversion between record ID and short URL

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
