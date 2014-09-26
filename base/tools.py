# import warnings
# import functools
# import traceback
# import os

import tornado.template

from configuration import config


# def deprecated(func):
#     """This is a decorator which can be used to mark functions
#     as deprecated. It will result in a warning being emitted
#     when the function is used."""
#
#     @functools.wraps(func)
#     def new_func(*args, **kwargs):
#         warnings.warn_explicit(
#             "Call to deprecated function {} from {}.".format(func.__name__, traceback.extract_stack()[-2]),
#             category=DeprecationWarning,
#             filename=func.__code__.co_filename,
#             lineno=func.__code__.co_firstlineno + 1
#         )
#         return func(*args, **kwargs)
#     return new_func
#
#
# def trace(func):
#     """This decorator simply prints when a function is called."""
#     @functools.wraps(func)
#     def new_func(*args, **kwargs):
#         print("Call to {} from {}".format(func.__name__, traceback.extract_stack()[-2]))
#         return func(*args, **kwargs)
#     return new_func


def english_join_list(l):
    """Join a list of strings into a comma and "and"-separated string.
    @type l: list
    @param l: The list to join.
    """
    l = [str(o) for o in l]
    if len(l) == 0:
        return ""
    if len(l) == 1:
        return l[0]
    if len(l) == 2:
        return l[0] + " and " + l[1]
    return ", ".join(l[0:-1]) + " and " + l[-1]


def plural_s(num, s="s"):
    """Return `s` if and only if abs(num) != 1. (For use in nouns.)"""
    if num == 1 or num == -1:
        return ""
    return s


def singular_s(num, s="s"):
    """Return `s` if and only if num == 1. (For use in verbs.)"""
    if num == 1:
        return s
    return ""


def a_or_number(num, a="a"):
    """If [num] is 1, return `a`, else return num."""
    if num == 1:
        return a
    else:
        return num


template_loader = tornado.template.Loader(config["template_path"])


# def ensure_symlink(source, name):
#     if os.path.isfile(name):
#         os.remove(name)
#     os.symlink(source, name)
