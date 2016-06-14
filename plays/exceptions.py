# -*- coding: utf-8 -*-
class PlaysException(Exception):
    def __init__(self, code=500, errors=[]):
        Exception.__init__(self)
        self.code = code
        self.errors = errors
