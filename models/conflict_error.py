# -*- coding: utf-8 -*-
class ConflictError(ValueError):
    def __init__(self, message, base, provided, merged):
        Exception.__init__(self, message)
        self.base = base
        self.provided = provided
        self.merged = merged
