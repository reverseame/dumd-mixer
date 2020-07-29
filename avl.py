#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''Defines an AVL tree structure and its common operations
'''

import random
from avlnode import AVLNode

import logging

__author__ = "Ricardo J. Rodríguez"
__copyright__ = "Copyright 2020, University of Zaragoza, Spain"
__credits__ = ["Ricardo J. Rodríguez"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Ricardo J. Rodríguez"
__email__ = "rjrodriguez@unizar.es"
__status__ = "Production"


def debug(msg):
    logging.debug(msg)

class AVLTree():
    def __init__(self):
        self.root = None

    def insert(self, key, value=None):
        '''
        Insert a new node in the AVL tree
        '''
        newnode = AVLNode(key, value)
        debug("[+] New node created: [{0}; {1}]".format(key, value))
        self.root = self._insert(self.root, newnode)

    def _insert(self, root: AVLNode, newnode: AVLNode) -> AVLNode:
        debug("[+] Inserting {0} (root: {1})".format(newnode, root))
        if not root: # base case, no tree
            return newnode
        elif newnode.key < root.key: # insert at the left, if the new node is smaller
            debug("[+] Going left")
            root.left = self._insert(root.left, newnode)
        elif newnode.key > root.key: # if greater, insert at the right
            debug("[+] Going right")
            root.right = self._insert(root.right, newnode)
        else:
            return root # no duplicates allowed

        # update height after insertion
        root.update_height()
        debug("[+] Updated height of node {0}".format(root))
        return self._rebalance(root)

    def _rebalance(self, root: AVLNode) -> AVLNode:
        '''
        Rebalance operations for a given tree node
        '''
        bf = root.get_balance_factor()
        if bf > 1:
            if root.right.get_height(root.right.right) > root.right.get_height(root.right.left): # left-left imbalance
                root = self._left_rotate(root)
            else: # right-left
                root = self._right_left_rotate(root)
        elif bf < -1:
            if root.left.get_height(root.left.left) > root.left.get_height(root.left.right): # right-right imbalance
                root = self._right_rotate(root)
            else: # left-rigth
                root = self._left_right_rotate(root)
            
        return root

    def _right_rotate(self, root: AVLNode) -> AVLNode:
        debug("[+] Right rotation ")
        tmp = root.left
        root.left = tmp.right
        tmp.right = root

        root.update_height()
        tmp.update_height()

        return tmp

    def _left_right_rotate(self, root: AVLNode) -> AVLNode:
        debug("[*] Left-Right rotation ")
        root.left = self._left_rotate(root.left)
        return self._right_rotate(root)
    
    def _left_rotate(self, root: AVLNode) -> AVLNode:
        debug("[+] Left rotation ")
        tmp = root.right
        root.right = tmp.left
        tmp.left = root

        root.update_height()
        tmp.update_height()

        return tmp

    def _right_left_rotate(self, root: AVLNode) -> AVLNode:
        debug("[+] Right-Left rotation ")
        root.right = self._right_rotate(root.right)
        return self._left_rotate(root)

    def _remove(self, root: AVLNode, key) -> AVLNode:
        # search the element, like a BST
        if root is None: # element not found
            return None
        elif key < root.key:
            root.left = self._remove(root.left, key)
        elif key > root.key:
            root.right = self._remove(root.right, key)
        else: # element found
            # check number of childrens
            if root.left is None and root.right is None:
                # no children
                return None
            elif root.left is None:
                # right children only
                root = root.right
            elif root.right is None:
                # left children only
                root = root.left
            else:
                # two children
                aux = self.find_min(root.right)
                root.update_content(aux)
                root.right = self.remove(root.right, aux.key)
        
        # update heights
        root.update_height()
        if root is not None:
            root = self._rebalance(root)

        return root
    
    def remove(self, key):
        '''
        Remove the node with key in the current tree, if exists
        '''
        if self.root is None:
            print('[-] AVL tree is empty!')
        else:
            self.root = self._remove(self.root, key)

    def _display(self, node: AVLNode, level=0, prefix=''):
        if node != None:
            print('{0}{1}{2}'.format('-'*level, prefix, node))
            if node.left != None:
                self._display(node.left, level + 1, '<')
            if node.right != None:
                self._display(node.right, level + 1, '>')

    def display(self):
        '''
        Display the current tree, using recursion
        '''
        debug("[+] Displaying the AVL ...")
        if self.root != None:
            self._display(self.root)
        else:
            print('[-] AVL tree is empty!')
    
    def _post_order(self, node: AVLNode):
        _str = ""
        if node is not None:
            _str = _str + self._post_order(node.left)
            _str = _str + self._post_order(node.right)
            _str = str(_str) + str(node) + ';'
        return _str

    def post_order(self, print_to_stdout=True):
        '''
        Display the current tree in post-order, using recursion
        As optional, it accepts a boolean to return the content. Otherwise, prints it
        '''
        _str = self._post_order(self.root)
        if print_to_stdout:
            print(_str)
        else:
            return _str
    
    def _pre_order(self, node: AVLNode):
        _str = ""
        if node is not None:
            _str = _str + str(node) + ';'
            _str = _str + self._pre_order(node.left)
            _str = _str + self._pre_order(node.right)
        return _str

    def pre_order(self, print_to_stdout=True):
        '''
        Display the current tree in pre-order, using recursion
        As optional, it accepts a boolean to return the content. Otherwise, prints it
        '''
        _str = self._pre_order(self.root)
        if print_to_stdout:
            print(_str)
        else:
            return _str

    def _in_order(self, node: AVLNode):
        _str = ""
        if node is not None:
            _str = _str + self._in_order(node.left)
            _str = _str + str(node) + ';'
            _str = _str + self._in_order(node.right)
        return _str

    def in_order(self, print_to_stdout=True):
        '''
        Display the current tree in order, using recursion
        As optional, it accepts a boolean to return the content. Otherwise, prints it
        '''
        _str = self._in_order(self.root)
        if print_to_stdout:
            print(_str)
        else:
            return _str

    def _find_max(self, root: AVLNode) -> AVLNode:
        if root.right is None:
            return root
        else:
            return self._find_max(root.right)

    def find_max(self) -> AVLNode:
        '''
        Find the maximum value of the current tree
        '''
        if self.root is None:
            print('[-] AVL tree is empty!')
            return None
        else:
            return self._find_max(self.root)

    def _find_min(self, root: AVLNode) -> AVLNode:
        if root.left is None:
            return root
        else:
            return self._find_min(root.left)

    def find_min(self) -> AVLNode:
        '''
        Find the minimum value of the current tree
        '''
        if self.root is None:
            print('[-] AVL tree is empty!')
            return None
        else:
            return self._find_min(self.root)

    def _search(self, root: AVLNode, key) -> AVLNode:
        if root is None:
            return None
        elif key < root.key:
            return self._search(root.left, key)
        elif key > root.key:
            return self._search(root.right, key)
        else: # otherwise, root is the element
            return root

    def search(self, key) -> AVLNode:
        '''
        Search a given key in the current tree
        '''
        if self.root is None:
            print('[-] AVL tree is empty!')
            return None
        else:
            return self._search(self.root, key)
    
    def exists(self, key) -> bool:
        '''
        Check whether a given key exists in the current tree
        '''
        if self.root is None:
            print('[-] AVL tree is empty!')
            return False
        else:
            return (self._search(self.root, key) is not None)

    def get_height(self) -> int:
        '''
        Return the height of the current tree
        '''
        if self.root is None:
            return 0
        else:
            return self.root.get_height()

    def _get_count(self, root: AVLNode) -> int:
        if root is None:
            return 0
        count = 1
        if root.left:
            count = count + self._get_count(root.left)
        if root.right:
            count = count + self._get_count(root.right)
        return count

    def get_count(self) -> int:
        '''
        Return the number of nodes of the current tree
        '''
        return self._get_count(self.root)

# unit test
if __name__ == "__main__":
    a = AVLTree()
    print("[*] Inserting random data ...")
    #randomlist = random.sample(range(0, 30), 5)
    randomlist = [18, 1, 13, 12, 3]
    print("[*] Data: " + str(randomlist))
    for i in randomlist:
        a.insert(i)

    #import pdb; pdb.set_trace()
    a.display()
    a.in_order()
    a.pre_order()
    a.post_order()
    print('Minimum key node: ' + str(a.find_min()))
    print('Maximum key node: ' + str(a.find_max()))

    print('Exists? ' + str(a.exists(randomlist[0])))
    print('Exists? ' + str(a.exists(-1)))
    
    a.remove(18)
    a.display()
    a.remove(3)
    a.display()

    a.insert(5)
    a.display()
    a.insert(3)
    a.display()
    a.insert(4)
    a.display()

    print('Number of nodes: ' + str(a.get_count()))

