"""
This implementation was taken from the functools.lru_cache and augmented to
include timed caching and caching aware rate limiting (i.e. if call results
are returned from the cache then that particular call does not affect the
rate limit)
"""

from collections import namedtuple
from functools import update_wrapper
from threading import RLock
from threading import Timer
from threading import Semaphore

_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])


class _HashedSeq(list):
    """ This class guarantees that hash() will be called no more than once
        per element.  This is important because the memorize() will hash
        the key multiple times on a cache miss.
    """

    __slots__ = 'hashvalue'

    def __init__(self, tup, hash=hash):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue


def _make_key(args, kwds, typed,
             kwd_mark = (object(),),
             fasttypes = {int, str, frozenset, type(None)},
             tuple=tuple, type=type, len=len):
    """Make a cache key from optionally typed positional and keyword arguments
    The key is constructed in a way that is flat as possible rather than
    as a nested structure that would take more memory.
    If there is only a single argument and its data type is known to cache
    its hash value, then that argument is returned without a wrapper.  This
    saves space and improves lookup speed.
    """
    # All of code below relies on kwds preserving the order input by the user.
    # Formerly, we sorted() the kwds before looping.  The new way is *much*
    # faster; however, it means that f(x=1, y=2) will now be treated as a
    # distinct call from f(y=2, x=1) which will be cached separately.
    key = args
    if kwds:
        key += kwd_mark
        for item in kwds.items():
            key += item
    if typed:
        key += tuple(type(v) for v in args)
        if kwds:
            key += tuple(type(v) for v in kwds.values())
    elif len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return _HashedSeq(key)


def memorize(maxsize=None, typed=False, timeout=None, calls=None, period=None, aware=False):
    """Least-recently-used cache decorator.
    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.
    If *typed* is True, arguments of different types will be cached separately.
    For example, f(3.0) and f(3) will be treated as distinct calls with
    distinct results.
    If *timeout* is set to an int or float, the cached values will be deleted
    after the number of seconds specified by it.
    If *calls* and *period* is set to an int and int/float respectively, the
    calls to this function will be limited to no more than x calls every
    y seconds/period.
    If *aware* is True, calls that are returned from the cache and not an
    actual call to the decorated function will not impact the rate limit.
    Arguments 'calls' and 'period' should either both be provided or neither.
    Arguments to the cached function must be hashable.
    View the cache statistics named tuple (hits, misses, maxsize, currsize)
    with f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.
    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used
    """
    # Users should only access memorize through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of memorize are encapsulated for thread safety

    # Early detection of an erroneous call to @memorize without any arguments
    # resulting in the inner function being passed to maxsize instead of an
    # integer or None.
    if maxsize is not None and not isinstance(maxsize, int):
        raise TypeError('Expected maxsize to be an integer or None')

    if timeout is not None and not isinstance(timeout, int) and not isinstance(timeout, float):
        raise TypeError('Expected timeout to be an integer, float or None')

    if bool(calls) ^ bool(period):
        raise ValueError("Expected for parameters 'calls' and 'period' to either both be provided "
                         "or neither be provided.")

    if calls is not None and not isinstance(calls, int):
        raise TypeError('Expected calls to be an integer or None')

    if period is not None and not isinstance(period, int) and not isinstance(period, float):
        raise TypeError('Expected period to be an integer, float or None')

    def decorating_function(user_function):
        wrapper = _memorize_wrapper(user_function, maxsize, typed, _CacheInfo, timeout, calls, period, aware)
        return update_wrapper(wrapper, user_function)

    return decorating_function


def _memorize_wrapper(user_function, maxsize, typed, _CacheInfo, timeout, calls, period, aware):
    # Constants shared by all memorize cache instances:
    sentinel = object()          # unique object used to signal cache misses
    make_key = _make_key         # build a key from the function arguments
    PREV, NEXT, KEY, RESULT = 0, 1, 2, 3   # names for the link fields

    cache = {}
    hits = misses = 0
    full = False
    cache_get = cache.get    # bound method to lookup a key or return None
    cache_len = cache.__len__  # get cache size without calling len()
    lock = RLock()           # because linkedlist updates aren't threadsafe
    root = []                # root of the circular doubly linked list
    root[:] = [root, root, None, None]     # initialize by pointing to self
    rated = bool(calls) and bool(period)   # indicator for rate limiting
    if rated:
        semaphore = Semaphore(calls)       # used to implement the rate limit

    if maxsize == 0:
        def wrapper(*args, **kwds):
            # No caching -- just a statistics update after a successful call
            if rated:
                semaphore.acquire()
            nonlocal misses
            result = user_function(*args, **kwds)
            misses += 1
            if rated:
                _start_timer(period, semaphore.release)
            return result

    elif maxsize is None:

        def wrapper(*args, **kwds):
            # Simple caching without ordering or size limit
            if rated and (not aware):
                semaphore.acquire()
            nonlocal hits, misses
            key = make_key(args, kwds, typed)
            result = cache_get(key, sentinel)
            if result is not sentinel:
                hits += 1
                if rated and (not aware):
                    _start_timer(period, semaphore.release)
                return result
            if rated and aware:
                semaphore.acquire()
            if rated:
                _start_timer(period, semaphore.release)
            result = user_function(*args, **kwds)
            cache[key] = result
            if timeout:
                _start_timer(timeout, _execute_timeout, [key])
            misses += 1
            return result

    else:
        def wrapper(*args, **kwds):
            # Size limited caching that tracks accesses by recency
            if rated and (not aware):
                semaphore.acquire()
            nonlocal root, hits, misses, full
            key = make_key(args, kwds, typed)
            with lock:
                link = cache_get(key)
                if link is not None:
                    # Move the link to the front of the circular queue
                    link_prev, link_next, _key, result = link
                    link_prev[NEXT] = link_next
                    link_next[PREV] = link_prev
                    last = root[PREV]
                    last[NEXT] = root[PREV] = link
                    link[PREV] = last
                    link[NEXT] = root
                    hits += 1
                    if rated and (not aware):
                        _start_timer(period, semaphore.release)
                    return result
            if rated and aware:
                semaphore.acquire()
            if rated:
                _start_timer(period, semaphore.release)
            result = user_function(*args, **kwds)
            with lock:
                if key in cache:
                    # Getting here means that this same key was added to the
                    # cache while the lock was released.  Since the link
                    # update is already done, we need only return the
                    # computed result and update the count of misses.
                    pass
                elif full:
                    # Use the old root to store the new key and result.
                    oldroot = root
                    oldroot[KEY] = key
                    oldroot[RESULT] = result
                    # Empty the oldest link and make it the new root.
                    # Keep a reference to the old key and old result to
                    # prevent their ref counts from going to zero during the
                    # update. That will prevent potentially arbitrary object
                    # clean-up code (i.e. __del__) from running while we're
                    # still adjusting the links.
                    root = oldroot[NEXT]
                    oldkey = root[KEY]
                    oldresult = root[RESULT]
                    root[KEY] = root[RESULT] = None
                    # Now update the cache dictionary.
                    del cache[oldkey]
                    # Save the potentially reentrant cache[key] assignment
                    # for last, after the root and links have been put in
                    # a consistent state.
                    cache[key] = oldroot
                    if timeout:
                        _start_timer(timeout, _execute_timeout, [key])
                else:
                    # Put result in a new link at the front of the queue.
                    last = root[PREV]
                    link = [last, root, key, result]
                    last[NEXT] = root[PREV] = cache[key] = link
                    if timeout:
                        _start_timer(timeout, _execute_timeout, [key])
                    # Use the cache_len bound method instead of the len() function
                    # which could potentially be wrapped in an memorize itself.
                    full = (cache_len() >= maxsize)
                misses += 1
            return result

    def _execute_timeout(key):
        with lock:
            cache.pop(key, None)

    def _start_timer(interval, funct, args=None):
        t = Timer(interval=interval, function=funct, args=args)
        t.setDaemon(True)
        t.start()

    def cache_info():
        """Report cache statistics"""
        with lock:
            return _CacheInfo(hits, misses, maxsize, cache_len())

    def cache_clear():
        """Clear the cache and cache statistics"""
        nonlocal hits, misses, full
        with lock:
            cache.clear()
            root[:] = [root, root, None, None]
            hits = misses = 0
            full = False

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper
