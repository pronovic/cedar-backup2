#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vim: set ft=python ts=3 sw=3 expandtab:
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
#              C E D A R
#          S O L U T I O N S       "Software done right."
#           S O F T W A R E
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Copyright (c) 2004-2005 Kenneth J. Pronovici.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License,
# Version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# Copies of the GNU General Public License are available from
# the Free Software Foundation website, http://www.gnu.org/.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Author   : Kenneth J. Pronovici <pronovic@ieee.org>
# Language : Python (>= 2.3)
# Project  : Cedar Backup, release 2
# Revision : $Id$
# Purpose  : Tests utility functionality.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# This file was created with a width of 132 characters, and NO tabs.

########################################################################
# Module documentation
########################################################################

"""
Unit tests for CedarBackup2/util.py.

Code Coverage
=============

   This module contains individual tests for the public functions and classes
   implemented in util.py.

Naming Conventions
==================

   I prefer to avoid large unit tests which validate more than one piece of
   functionality, and I prefer to avoid using overly descriptive (read: long)
   test names, as well.  Instead, I use lots of very small tests that each
   validate one specific thing.  These small tests are then named with an index
   number, yielding something like C{testAddDir_001} or C{testValidate_010}.
   Each method has a docstring describing what it's supposed to accomplish.  I
   feel that this makes it easier to judge how important a given failure is,
   and also makes it somewhat easier to diagnose and fix individual problems.

Full vs. Reduced Tests
======================

   All of the tests in this module are considered safe to be run in an average
   build environment.  There is a no need to use a UTILTESTS_FULL environment
   variable to provide a "reduced feature set" test suite as for some of the
   other test modules.

@author Kenneth J. Pronovici <pronovic@ieee.org>
"""


########################################################################
# Import modules and do runtime validations
########################################################################

# Import standard modules
import unittest
from os.path import isdir
from CedarBackup2.util import executeCommand, getFunctionReference, UnorderedList


#######################################################################
# Test Case Classes
#######################################################################

##########################
# TestUnorderedList class
##########################

class TestUnorderedList(unittest.TestCase):

   """Tests for the UnorderedList class."""

   ################
   # Setup methods
   ################

   def setUp(self):
      pass

   def tearDown(self):
      pass


   ##################################
   # Test unordered list comparisons
   ##################################

   def testComparison_001(self):
      """
      Test two empty lists.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      self.failUnlessEqual(list1, list2)
      self.failUnlessEqual(list2, list1)

   def testComparison_002(self):
      """
      Test empty vs. non-empty list.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      self.failUnlessEqual([1,2,3,4,], list1)
      self.failUnlessEqual([2,3,4,1,], list1)
      self.failUnlessEqual([3,4,1,2,], list1)
      self.failUnlessEqual([4,1,2,3,], list1)
      self.failUnlessEqual(list1, [4,3,2,1,])
      self.failUnlessEqual(list1, [3,2,1,4,])
      self.failUnlessEqual(list1, [2,1,4,3,])
      self.failUnlessEqual(list1, [1,4,3,2,])
      self.failIfEqual(list1, list2)
      self.failIfEqual(list2, list1)

   def testComparison_003(self):
      """
      Test two non-empty lists, completely different contents.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      list2.append('a')
      list2.append('b')
      list2.append('c')
      list2.append('d')
      self.failUnlessEqual([1,2,3,4,], list1)
      self.failUnlessEqual([2,3,4,1,], list1)
      self.failUnlessEqual([3,4,1,2,], list1)
      self.failUnlessEqual([4,1,2,3,], list1)
      self.failUnlessEqual(list1, [4,3,2,1,])
      self.failUnlessEqual(list1, [3,2,1,4,])
      self.failUnlessEqual(list1, [2,1,4,3,])
      self.failUnlessEqual(list1, [1,4,3,2,])
      self.failUnlessEqual(['a','b','c','d',], list2)
      self.failUnlessEqual(['b','c','d','a',], list2)
      self.failUnlessEqual(['c','d','a','b',], list2)
      self.failUnlessEqual(['d','a','b','c',], list2)
      self.failUnlessEqual(list2, ['d','c','b','a',])
      self.failUnlessEqual(list2, ['c','b','a','d',])
      self.failUnlessEqual(list2, ['b','a','d','c',])
      self.failUnlessEqual(list2, ['a','d','c','b',])
      self.failIfEqual(list1, list2)
      self.failIfEqual(list2, list1)

   def testComparison_004(self):
      """
      Test two non-empty lists, different but overlapping contents.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      list2.append(3)
      list2.append(4)
      list2.append('a')
      list2.append('b')
      self.failUnlessEqual([1,2,3,4,], list1)
      self.failUnlessEqual([2,3,4,1,], list1)
      self.failUnlessEqual([3,4,1,2,], list1)
      self.failUnlessEqual([4,1,2,3,], list1)
      self.failUnlessEqual(list1, [4,3,2,1,])
      self.failUnlessEqual(list1, [3,2,1,4,])
      self.failUnlessEqual(list1, [2,1,4,3,])
      self.failUnlessEqual(list1, [1,4,3,2,])
      self.failUnlessEqual([3,4,'a','b',], list2)
      self.failUnlessEqual([4,'a','b',3,], list2)
      self.failUnlessEqual(['a','b',3,4,], list2)
      self.failUnlessEqual(['b',3,4,'a',], list2)
      self.failUnlessEqual(list2, ['b','a',4,3,])
      self.failUnlessEqual(list2, ['a',4,3,'b',])
      self.failUnlessEqual(list2, [4,3,'b','a',])
      self.failUnlessEqual(list2, [3,'b','a',4,])
      self.failIfEqual(list1, list2)
      self.failIfEqual(list2, list1)

   def testComparison_005(self):
      """
      Test two non-empty lists, exactly the same contents, same order.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      list2.append(1)
      list2.append(2)
      list2.append(3)
      list2.append(4)
      self.failUnlessEqual([1,2,3,4,], list1)
      self.failUnlessEqual([2,3,4,1,], list1)
      self.failUnlessEqual([3,4,1,2,], list1)
      self.failUnlessEqual([4,1,2,3,], list1)
      self.failUnlessEqual(list1, [4,3,2,1,])
      self.failUnlessEqual(list1, [3,2,1,4,])
      self.failUnlessEqual(list1, [2,1,4,3,])
      self.failUnlessEqual(list1, [1,4,3,2,])
      self.failUnlessEqual([1,2,3,4,], list2)
      self.failUnlessEqual([2,3,4,1,], list2)
      self.failUnlessEqual([3,4,1,2,], list2)
      self.failUnlessEqual([4,1,2,3,], list2)
      self.failUnlessEqual(list2, [4,3,2,1,])
      self.failUnlessEqual(list2, [3,2,1,4,])
      self.failUnlessEqual(list2, [2,1,4,3,])
      self.failUnlessEqual(list2, [1,4,3,2,])
      self.failUnlessEqual(list1, list2)
      self.failUnlessEqual(list2, list1)

   def testComparison_006(self):
      """
      Test two non-empty lists, exactly the same contents, different order.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      list2.append(3)
      list2.append(1)
      list2.append(2)
      list2.append(4)
      self.failUnlessEqual([1,2,3,4,], list1)
      self.failUnlessEqual([2,3,4,1,], list1)
      self.failUnlessEqual([3,4,1,2,], list1)
      self.failUnlessEqual([4,1,2,3,], list1)
      self.failUnlessEqual(list1, [4,3,2,1,])
      self.failUnlessEqual(list1, [3,2,1,4,])
      self.failUnlessEqual(list1, [2,1,4,3,])
      self.failUnlessEqual(list1, [1,4,3,2,])
      self.failUnlessEqual([1,2,3,4,], list2)
      self.failUnlessEqual([2,3,4,1,], list2)
      self.failUnlessEqual([3,4,1,2,], list2)
      self.failUnlessEqual([4,1,2,3,], list2)
      self.failUnlessEqual(list2, [4,3,2,1,])
      self.failUnlessEqual(list2, [3,2,1,4,])
      self.failUnlessEqual(list2, [2,1,4,3,])
      self.failUnlessEqual(list2, [1,4,3,2,])
      self.failUnlessEqual(list1, list2)
      self.failUnlessEqual(list2, list1)

   def testComparison_007(self):
      """
      Test two non-empty lists, exactly the same contents, some duplicates,
      same order.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      list1.append(4)
      list2.append(1)
      list2.append(2)
      list2.append(2)
      list2.append(3)
      list2.append(4)
      list2.append(4)
      self.failUnlessEqual([1,2,2,3,4,4,], list1)
      self.failUnlessEqual([2,2,3,4,1,4,], list1)
      self.failUnlessEqual([2,3,4,1,4,2,], list1)
      self.failUnlessEqual([2,4,1,4,2,3,], list1)
      self.failUnlessEqual(list1, [1,2,2,3,4,4,])
      self.failUnlessEqual(list1, [2,2,3,4,1,4,])
      self.failUnlessEqual(list1, [2,3,4,1,4,2,])
      self.failUnlessEqual(list1, [2,4,1,4,2,3,])
      self.failUnlessEqual([1,2,2,3,4,4,], list2)
      self.failUnlessEqual([2,2,3,4,1,4,], list2)
      self.failUnlessEqual([2,3,4,1,4,2,], list2)
      self.failUnlessEqual([2,4,1,4,2,3,], list2)
      self.failUnlessEqual(list2, [1,2,2,3,4,4,])
      self.failUnlessEqual(list2, [2,2,3,4,1,4,])
      self.failUnlessEqual(list2, [2,3,4,1,4,2,])
      self.failUnlessEqual(list2, [2,4,1,4,2,3,])
      self.failUnlessEqual(list1, list2)
      self.failUnlessEqual(list2, list1)

   def testComparison_008(self):
      """
      Test two non-empty lists, exactly the same contents, some duplicates,
      different order.
      """
      list1 = UnorderedList()
      list2 = UnorderedList()
      list1.append(1)
      list1.append(2)
      list1.append(2)
      list1.append(3)
      list1.append(4)
      list1.append(4)
      list2.append(3)
      list2.append(1)
      list2.append(2)
      list2.append(2)
      list2.append(4)
      list2.append(4)
      self.failUnlessEqual([1,2,2,3,4,4,], list1)
      self.failUnlessEqual([2,2,3,4,1,4,], list1)
      self.failUnlessEqual([2,3,4,1,4,2,], list1)
      self.failUnlessEqual([2,4,1,4,2,3,], list1)
      self.failUnlessEqual(list1, [1,2,2,3,4,4,])
      self.failUnlessEqual(list1, [2,2,3,4,1,4,])
      self.failUnlessEqual(list1, [2,3,4,1,4,2,])
      self.failUnlessEqual(list1, [2,4,1,4,2,3,])
      self.failUnlessEqual([1,2,2,3,4,4,], list2)
      self.failUnlessEqual([2,2,3,4,1,4,], list2)
      self.failUnlessEqual([2,3,4,1,4,2,], list2)
      self.failUnlessEqual([2,4,1,4,2,3,], list2)
      self.failUnlessEqual(list2, [1,2,2,3,4,4,])
      self.failUnlessEqual(list2, [2,2,3,4,1,4,])
      self.failUnlessEqual(list2, [2,3,4,1,4,2,])
      self.failUnlessEqual(list2, [2,4,1,4,2,3,])
      self.failUnlessEqual(list1, list2)
      self.failUnlessEqual(list2, list1)


######################
# TestFunctions class
######################

class TestFunctions(unittest.TestCase):

   """Tests for the various public functions."""

   ################
   # Setup methods
   ################

   def setUp(self):
      pass

   def tearDown(self):
      pass


   ##############################
   # Test getFunctionReference() 
   ##############################
         
   def testGetFunctionReference_001(self):
      """
      Check that the search works within "standard" Python namespace.
      """
      module = "os.path"
      function = "isdir"
      reference = getFunctionReference(module, function)
      self.failUnless(isdir is reference)

   def testGetFunctionReference_002(self):
      """
      Check that the search works for things within CedarBackup2.
      """
      module = "CedarBackup2.util"
      function = "executeCommand"
      reference = getFunctionReference(module, function)
      self.failUnless(executeCommand is reference)


   ########################
   # Test executeCommand() 
   ########################
         
   def testExecuteCommand_001(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=False
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_002(self):
      """
      Execute a command that should succeed, one argument, returnOutput=False
      Command-line: python -V
      """
      command=["python", ]
      args=["-V", ]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_003(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=False
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)"
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(0)", ]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_004(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=False
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", ]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_005(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=False
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_006(self):
      """
      Execute a command that should fail, returnOutput=False
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)"
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(1)", ]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_007(self):
      """
      Execute a command that should fail, more arguments, returnOutput=False
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(1)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_008(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=True
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_009(self):
      """
      Execute a command that should succeed, one argument, returnOutput=True
      Command-line: python -V
      """
      command=["python", ]
      args=["-V", ]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnless(output[0].startswith("Python"))

   def testExecuteCommand_010(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=True
      Command-line: python -c "import sys; print ''; sys.exit(0)"
      """
      command=["python", ]
      args=["-c", "import sys; print ''; sys.exit(0)", ]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_011(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=True
      Command-line: python -c "import sys; print '%s' % (sys.argv[1]); sys.exit(0)" first
      """
      command=["python", ]
      args=["-c", "import sys; print '%s' % (sys.argv[1]); sys.exit(0)", "first", ]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("first\n", output[0])

   def testExecuteCommand_012(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=True
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_013(self):
      """
      Execute a command that should fail, returnOutput=True
      Command-line: python -c "import sys; print ''; sys.exit(1)"
      """
      command=["python", ]
      args=["-c", "import sys; print ''; sys.exit(1)", ]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_014(self):
      """
      Execute a command that should fail, more arguments, returnOutput=True
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_015(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_016(self):
      """
      Execute a command that should succeed, one argument, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -V
      """
      command=["python", "-V", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_017(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)"
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(0)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_018(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_019(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first second
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_020(self):
      """
      Execute a command that should fail, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)"
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(1)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_021(self):
      """
      Execute a command that should fail, more arguments, returnOutput=False
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)" first second
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(1)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_022(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_023(self):
      """
      Execute a command that should succeed, one argument, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -V
      """
      command=["python", "-V"]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnless(output[0].startswith("Python"))

   def testExecuteCommand_024(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print ''; sys.exit(0)"
      """
      command=["python", "-c", "import sys; print ''; sys.exit(0)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_025(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print '%s' % (sys.argv[1]); sys.exit(0)" first
      """
      command=["python", "-c", "import sys; print '%s' % (sys.argv[1]); sys.exit(0)", "first", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("first\n", output[0])

   def testExecuteCommand_026(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)" first second
      """
      command=["python", "-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_027(self):
      """
      Execute a command that should fail, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print ''; sys.exit(1)"
      """
      command=["python", "-c", "import sys; print ''; sys.exit(1)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_028(self):
      """
      Execute a command that should fail, more arguments, returnOutput=True
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)" first second
      """
      command=["python", "-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_030(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=False, ignoring stderr.
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_031(self):
      """
      Execute a command that should succeed, one argument, returnOutput=False, ignoring stderr.
      Command-line: python -V
      """
      command=["python", ]
      args=["-V", ]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_032(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=False, ignoring stderr.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)"
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(0)", ]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_033(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=False, ignoring stderr.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", ]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_034(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=False, ignoring stderr.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_035(self):
      """
      Execute a command that should fail, returnOutput=False, ignoring stderr.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)"
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(1)", ]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_036(self):
      """
      Execute a command that should fail, more arguments, returnOutput=False, ignoring stderr.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print sys.argv[1:]; sys.exit(1)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_037(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=True, ignoring stderr.
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_038(self):
      """
      Execute a command that should succeed, one argument, returnOutput=True, ignoring stderr.
      Command-line: python -V
      """
      command=["python", ]
      args=["-V", ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(0, len(output))

   def testExecuteCommand_039(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=True, ignoring stderr.
      Command-line: python -c "import sys; print ''; sys.exit(0)"
      """
      command=["python", ]
      args=["-c", "import sys; print ''; sys.exit(0)", ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_040(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=True, ignoring stderr.
      Command-line: python -c "import sys; print '%s' % (sys.argv[1]); sys.exit(0)" first
      """
      command=["python", ]
      args=["-c", "import sys; print '%s' % (sys.argv[1]); sys.exit(0)", "first", ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("first\n", output[0])

   def testExecuteCommand_041(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=True, ignoring stderr.
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_042(self):
      """
      Execute a command that should fail, returnOutput=True, ignoring stderr.
      Command-line: python -c "import sys; print ''; sys.exit(1)"
      """
      command=["python", ]
      args=["-c", "import sys; print ''; sys.exit(1)", ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_043(self):
      """
      Execute a command that should fail, more arguments, returnOutput=True, ignoring stderr.
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)" first second
      """
      command=["python", ]
      args=["-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)", "first", "second", ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_044(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_045(self):
      """
      Execute a command that should succeed, one argument, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -V
      """
      command=["python", "-V", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_046(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)"
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(0)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_047(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_048(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(0)" first second
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(0)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_049(self):
      """
      Execute a command that should fail, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)"
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(1)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_050(self):
      """
      Execute a command that should fail, more arguments, returnOutput=False, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print sys.argv[1:]; sys.exit(1)" first second
      """
      command=["python", "-c", "import sys; print sys.argv[1:]; sys.exit(1)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=False, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(None, output)

   def testExecuteCommand_051(self):
      """
      Execute a command that should succeed, no arguments, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: echo
      """
      command=["echo", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_052(self):
      """
      Execute a command that should succeed, one argument, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -V
      """
      command=["python", "-V"]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(0, len(output))

   def testExecuteCommand_053(self):
      """
      Execute a command that should succeed, two arguments, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print ''; sys.exit(0)"
      """
      command=["python", "-c", "import sys; print ''; sys.exit(0)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_054(self):
      """
      Execute a command that should succeed, three arguments, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print '%s' % (sys.argv[1]); sys.exit(0)" first
      """
      command=["python", "-c", "import sys; print '%s' % (sys.argv[1]); sys.exit(0)", "first", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("first\n", output[0])

   def testExecuteCommand_055(self):
      """
      Execute a command that should succeed, four arguments, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)" first second
      """
      command=["python", "-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(0)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failUnlessEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])

   def testExecuteCommand_056(self):
      """
      Execute a command that should fail, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print ''; sys.exit(1)"
      """
      command=["python", "-c", "import sys; print ''; sys.exit(1)", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(1, len(output))
      self.failUnlessEqual("\n", output[0])

   def testExecuteCommand_057(self):
      """
      Execute a command that should fail, more arguments, returnOutput=True, ignoring stderr.
      Do this all bundled into the command list, just to check that this works as expected.
      Command-line: python -c "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)" first second
      """
      command=["python", "-c", "import sys; print '%s' % sys.argv[1]; print '%s' % sys.argv[2]; sys.exit(1)", "first", "second", ]
      args=[]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=True)
      self.failIfEqual(0, result)
      self.failUnlessEqual(2, len(output))
      self.failUnlessEqual("first\n", output[0])
      self.failUnlessEqual("second\n", output[1])


#######################################################################
# Suite definition
#######################################################################

def suite():
   """Returns a suite containing all the test cases in this module."""
   return unittest.TestSuite((
                              unittest.makeSuite(TestUnorderedList, 'test'),
                              unittest.makeSuite(TestFunctions, 'test'),
                            ))


########################################################################
# Module entry point
########################################################################

# When this module is executed from the command-line, run its tests
if __name__ == '__main__':
   unittest.main()

