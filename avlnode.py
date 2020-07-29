#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''Auxiliary class to define the node of an AVL tree

A node is composed of a key and a value (optionally None). This abstraction enables you to use the AVL as a structure to store elements with an associated key.
'''

__author__ = "Ricardo J. Rodríguez"
__copyright__ = "Copyright 2020, University of Zaragoza, Spain"
__credits__ = ["Ricardo J. Rodríguez"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Ricardo J. Rodríguez"
__email__ = "rjrodriguez@unizar.es"
__status__ = "Production"

class AVLNode:
    def __init__(self, key, value=None):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.height = 1 

    def __str__(self):
        #_str = '{0}[{1}:{2}]{3}'.format(self.key, self.height, self.get_balance_factor(), 'L' if self._is_leaf() else ' ')
        _str = '{0}{1}'.format(self.key, '[' + str(self.value) + ']' if self.value is not None else '')
        return _str

    def _is_leaf(self) -> bool:
        return (self.left == None and self.right == None)

    def get_balance_factor(self) -> int:
        return self.get_height(self.right) - self.get_height(self.left)

    def get_height(self) -> int:
        return self.height

    def get_height(self, node) -> int:
        if node is None:
            return 0
        else:
            return node.height
    
    def is_unbalanced(self) -> bool:
        return (abs(self.get_balance_factor()) == 2)

    def update_height(self):
        self.height = max(self.get_height(self.left), self.get_height(self.right)) + 1

    def update_content(self, node):
        # updates the content values
        self.key = node.key
        self.value = node.value

