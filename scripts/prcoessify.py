# from a comment on https://stackoverflow.com/a/2046630/4354423
# from https://gist.github.com/schlamar/2311116
# allows to execute a single python function in a sub-process
# adjusted by Erik Brendel to python3 and using exception chaining
# helpful, when certain libraries cannot properly clean up their file handles
# (looking at you, GitPython), and everything crashes because of "Too Many Open Files"

import os
import sys
import traceback
from functools import wraps
from multiprocessing import Process, Queue


def processify(func):
    """Decorator to run a function as a process.
    Be sure that every argument and the return value
    is *pickable*.
    The created process is joined, so the code does not
    run in parallel.
    """

    def process_func(q, *args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except Exception as e:
            error = e
            ret = None
        else:
            error = None

        q.put((ret, error))

    # register original function with different name
    # in sys.modules so it is pickable
    process_func.__name__ = func.__name__ + 'processify_func'
    setattr(sys.modules[__name__], process_func.__name__, process_func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        q = Queue()
        p = Process(target=process_func, args=[q] + list(args), kwargs=kwargs)
        p.start()
        ret, error = q.get()
        p.join()

        if error:
            raise Exception("Subprocess failed") from error

        return ret
    return wrapper


@processify
def test_function():
    return os.getpid()


@processify
def test_deadlock():
    return range(30000)


@processify
def test_exception():
    raise RuntimeError('xyz')


def test():
    print(os.getpid())
    print(test_function())
    print(len(test_deadlock()))
    test_exception()


if __name__ == '__main__':
    test()
