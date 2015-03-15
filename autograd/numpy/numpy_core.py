from __future__ import absolute_import
from functools import partial
from numpy import *
import numpy as np_orig
# ----- Objects in numpy.__dict__ not imported by * -----
int     = np_orig.int
unicode = np_orig.unicode
complex = np_orig.complex
long    = np_orig.long
abs     = np_orig.abs
bool    = np_orig.bool
float   = np_orig.float
max     = np_orig.max
object  = np_orig.object
min     = np_orig.min
str     = np_orig.str
round   = np_orig.round

# ----- Numpy gradients -----

from autograd.core import primitive, getval, untake
P = primitive
isarray = lambda x : isinstance(getval(x), ndarray)
I = lambda x : x # Identity operator

abs    = P(abs,    lambda ans, x : [lambda g : sign(x) * g])
exp    = P(exp,    lambda ans, x : [lambda g : ans * g])
log    = P(log,    lambda ans, x : [lambda g : g / x])
sin    = P(sin,    lambda ans, x : [lambda g : g * cos(x)])
cos    = P(cos,    lambda ans, x : [lambda g : - g * sin(x)])
tan    = P(tan,    lambda ans, x : [lambda g : g / cos(x) **2])
sinh   = P(sinh,   lambda ans, x : [lambda g : g * cosh(x)])
cosh   = P(cosh,   lambda ans, x : [lambda g : g * sinh(x)])
tanh   = P(tanh,   lambda ans, x : [lambda g : g / cosh(x) **2])
square = P(square, lambda ans, x : [lambda g : g * 2 * x])
sqrt   = P(sqrt,   lambda ans, x : [lambda g : g * 0.5 * x**-0.5])
sign   = P(sign,   lambda ans, x : [lambda g : 0.0])
full   = P(full,   lambda ans, shape, fill_value : [None, lambda g :  sum(g)])
reshape     = P(reshape,     lambda ans, x, shape, order=None : [lambda g : reshape(g, x.shape, order=order)])
ravel       = P(ravel,       lambda ans, x, order=None   : [lambda g : reshape(g, x.shape, order=order)])
expand_dims = P(expand_dims, lambda ans, x, axis         : [lambda g : squeeze(g, axis)])
squeeze     = P(squeeze,     lambda ans, x, axis         : [lambda g : repeat(g, x.shape[axis], axis)])
repeat      = P(repeat,      lambda ans, x, shape, axis  : [lambda g : sum(g, axis, keepdims=True)])
transpose   = P(transpose,   lambda ans, x               : [lambda g : transpose(g)])
split       = P(split,       lambda ans, x, idxs, axis=0 : [lambda g : concatenate(g, axis=axis)])
diag        = P(diag,        lambda ans, x               : [lambda g : diag(g)])
trace       = P(trace,       lambda ans, x               : [lambda g : g * eye(x.shape[0])])

# ----- More subtle gradients -----

def make_grad_np_sum(ans, x, axis=None, keepdims=False):
    if not isarray(x):
        return [I]
    shape = x.shape
    if axis is None:
        return [lambda g : full(shape, g)]
    else:
        if keepdims:
            return [lambda g : repeat(g, shape[axis], axis)]
        else:
            return [lambda g : repeat(expand_dims(g, axis),
                                         shape[axis], axis)]
sum = P(sum, make_grad_np_sum)

def make_grad_np_mean(ans, x, axis=None, keepdims=False):
    if not isarray(x):
        return [I]
    shape = x.shape
    if axis is None:
        return [lambda g : full(shape, g) / prod(shape)]
    else:
        if keepdims:
            return [lambda g : repeat(g, shape[axis], axis) / shape[axis]]
        else:
            return [lambda g : repeat(expand_dims(g, axis),
                                         shape[axis], axis) / shape[axis]]
mean = P(mean, make_grad_np_mean)

def make_grad_np_max(ans, x):
    def gradfun(g):
        idxs = argmax(getval(x))
        return untake(g, unravel_index(idxs, x.shape))
    return [gradfun]
max = P(max, make_grad_np_max)

def make_grad_np_dot(ans, A, B):
    def grad_np_dot_A(g):
        if B.ndim is 2:
            return dot(g, B.T)
        elif A.ndim is 2:
            return outer(g, B)
        else:
            return g * B
    def grad_np_dot_B(g):
        if A.ndim is 2:
            return dot(A.T, g)
        elif B.ndim is 2:
            return outer(A, g)
        else:
            return g * A
    return [grad_np_dot_A, grad_np_dot_B]
dot = P(dot, make_grad_np_dot)

def make_grad_np_concatenate(ans, arr_list, axis=0):
    def grad_np_concatenate(g):
        idxs = cumsum([a.shape[axis] for a in getval(arr_list)[:-1]])
        return split(g, idxs, axis=axis)
    return [grad_np_concatenate]
concatenate = P(concatenate, make_grad_np_concatenate)

# ----- Special list constructor -----

class ArgnumGrad(object):
    def __init__(self, fun_with_argnum):
        self.fun = fun_with_argnum
    def __getitem__(self, argnum):
        return partial(self.fun, argnum)

def kylist(*args):
    return list(args)
kylist = primitive(kylist, lambda ans, *args : ArgnumGrad(lambda argnum, g : g[argnum]))

# Wrap the concatenation function to automatically wrap the list into a kylist.
unwrapped_np_concatenate = concatenate
def concatwrapper(*args, **kwargs):
    args = (kylist(*(args[0])),) + args[1:]
    return unwrapped_np_concatenate(*args, **kwargs)
concatenate = concatwrapper
