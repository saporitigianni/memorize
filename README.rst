.. -*-restructuredtext-*-

memorize: A caching package with options for timed caching and caching aware rate limiting
==========================================================================================

.. image:: https://img.shields.io/badge/Made%20with-Python-1f425f.svg
    :target: https://www.python.org/

.. image:: https://img.shields.io/pypi/v/memorize.svg
    :target: https://pypi.org/project/memorize/

.. image:: https://img.shields.io/pypi/l/memorize.svg
    :target: https://pypi.org/project/memorize/

.. image:: https://img.shields.io/pypi/pyversions/memorize.svg
    :target: https://pypi.org/project/memorize/

Installation
------------

To install memorize, simply use pip:

.. code:: bash

    $ pip install memorize

or install directly from source to include latest changes:

.. code:: bash

    $ pip install git+https://github.com/saporitigianni/memorize.git

or clone and then install:

.. code:: bash

    $ git clone https://github.com/saporitigianni/memorize.git
    $ cd memorize
    $ python3 setup.py install

Usage
-----

This class extends the functools.lru_cache functionality to add timed caching and caching aware rate limiting
(e.g. if call results are returned from the cache then that particular call does not affect the rate limit)

**Constraints:**
 - Since a dictionary is used to cache results, the positional and keyword arguments to the function must be hashable (NOT lists, dicts, sets, or any other object that does not define hash())
 - It is very important to use the parenthesis even if empty: **@memorize()** NOT **@memorize**
 - When rate limiting, both the **calls** and **period** arguments must be provided otherwise an error is raised

**Default Settings:**
 - timeout = None
 - maxsize = None
 - typed = False
 - calls = None
 - period = None
 - aware = False

.. code:: python

    from memorize import memorize

    # If you want to use all default settings
    @memorize()
    def fib(n):
        if n < 2:
            return n
        else:
            return fib(n-2) + fib(n-1)

    # With memorization fib(20) will be run 21 times instead of 21891 times
    # without memorization
    fib(20)

    # If you want to cache a maximum of 128 calls, separated by different types,
    # each for 10 seconds use:
    @memorize(timeout=10, maxsize=128, typed=True)

    # If you want to implement caching aware rate limiting then use the following:
    # This will limit to no more than 10 calls for every 60 second period and if a
    # result is returned from the cache it does not count towards the 10 calls.
    @memorize(calls=10, period=60, aware=True)


Contributing
------------

Please read the `CONTRIBUTING <https://github.com/saporitigianni/memorize/blob/master/CONTRIBUTING.md>`_ document before making changes that you would like adopted in the code.

Code of Conduct
---------------

Everyone interacting in the ``memorize`` project's codebase, issue
trackers, chat rooms, and mailing lists is expected to follow the
`PyPA Code of Conduct <https://www.pypa.io/en/latest/code-of-conduct/>`_.:octocat:

|
|
| ETH 0xaD1F09626b9B8e701D5f0F4a237193Df73d3C445
| BTC 199zsVqCusefv8yjdYQhUQZmLCyh75dqNV
| LTC LUBqs7VxC43ttPsQuM1jaZFmshKTAU1Rs9
