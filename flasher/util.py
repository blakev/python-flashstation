"""Misc. helper functions."""


def pipe(ins):
    return [c + '\n' for c in ins]


def all_eq(val, seq):
    for obj in seq:
        if obj != val:
            return False
    return True


def dev_name(tup):
    return '_'.join(map(hex, map(int, tup)))
