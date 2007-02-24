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
# Copyright (c) 2007 Kenneth J. Pronovici.
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
# Purpose  : Tests action utility functionality.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

########################################################################
# Module documentation
########################################################################

"""
Unit tests for CedarBackup2/actions/util.py.

Code Coverage
=============

   This module contains individual tests for the public functions and classes
   implemented in actions/util.py. 

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
   build environment.  There is a no need to use a ACTIONSUTILTESTS_FULL
   environment variable to provide a "reduced feature set" test suite as for
   some of the other test modules.

@author Kenneth J. Pronovici <pronovic@ieee.org>
"""


########################################################################
# Import modules and do runtime validations
########################################################################

import sys
import os
import unittest
import tempfile
import tarfile
from CedarBackup2.testutil import findResources, buildPath, removedir, extractTar
from CedarBackup2.actions.util import findDailyDirs, writeIndicatorFile
from CedarBackup2.extend.encrypt import ENCRYPT_INDICATOR


#######################################################################
# Module-wide configuration and constants
#######################################################################

DATA_DIRS = [ "./data", "./test/data", ]
RESOURCES = [ "tree1.tar.gz", "tree8.tar.gz", "tree15.tar.gz", "tree17.tar.gz",
              "tree18.tar.gz", "tree19.tar.gz", "tree20.tar.gz", ]

INVALID_PATH = "bogus"  # This path name should never exist


#######################################################################
# Test Case Classes
#######################################################################

######################
# TestFunctions class
######################

class TestFunctions(unittest.TestCase):

   """Tests for the various public functions."""

   ################
   # Setup methods
   ################

   def setUp(self):
      try:
         self.tmpdir = tempfile.mkdtemp()
         self.resources = findResources(RESOURCES, DATA_DIRS)
      except Exception, e:
         self.fail(e)

   def tearDown(self):
      try:
         removedir(self.tmpdir)
      except: pass 


   ##################
   # Utility methods
   ##################

   def extractTar(self, tarname):
      """Extracts a tarfile with a particular name."""
      extractTar(self.tmpdir, self.resources['%s.tar.gz' % tarname])

   def buildPath(self, components):
      """Builds a complete search path from a list of components."""
      components.insert(0, self.tmpdir)
      return buildPath(components)


   #######################
   # Test findDailyDirs()
   #######################

   def testFindDailyDirs_001(self):
      """
      Test with a nonexistent staging directory.
      """
      stagingDir = self.buildPath([INVALID_PATH])
      self.failUnlessRaises(ValueError, findDailyDirs, stagingDir, ENCRYPT_INDICATOR)

   def testFindDailyDirs_002(self):
      """
      Test with an empty staging directory.
      """
      self.extractTar("tree8")
      stagingDir = self.buildPath(["tree8", "dir001",])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_003(self):
      """
      Test with a staging directory containing only files.
      """
      self.extractTar("tree1")
      stagingDir = self.buildPath(["tree1",])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_004(self):
      """
      Test with a staging directory containing only links.
      """
      self.extractTar("tree15")
      stagingDir = self.buildPath(["tree15", "dir001", ])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_005(self):
      """
      Test with a valid staging directory, where the daily directories do NOT
      contain the encrypt indicator.
      """
      self.extractTar("tree17")  
      stagingDir = self.buildPath(["tree17" ])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual(6, len(dailyDirs))
      self.failUnless(self.buildPath([ "tree17", "2006", "12", "29", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree17", "2006", "12", "30", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree17", "2006", "12", "31", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree17", "2007", "01", "01", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree17", "2007", "01", "02", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree17", "2007", "01", "03", ]) in dailyDirs)

   def testFindDailyDirs_006(self):
      """
      Test with a valid staging directory, where the daily directories DO
      contain the encrypt indicator.
      """
      self.extractTar("tree18")
      stagingDir = self.buildPath(["tree18" ])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_007(self):
      """
      Test with a valid staging directory, where some daily directories contain
      the encrypt indicator and others do not.
      """
      self.extractTar("tree19")
      stagingDir = self.buildPath(["tree19" ])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual(3, len(dailyDirs))
      self.failUnless(self.buildPath([ "tree19", "2006", "12", "30", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree19", "2007", "01", "01", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree19", "2007", "01", "03", ]) in dailyDirs)

   def testFindDailyDirs_008(self):
      """
      Test for case where directories other than daily directories contain the
      encrypt indicator (the indicator should be ignored).
      """
      self.extractTar("tree20")
      stagingDir = self.buildPath(["tree20", ])
      dailyDirs = findDailyDirs(stagingDir, ENCRYPT_INDICATOR)
      self.failUnlessEqual(6, len(dailyDirs))
      self.failUnless(self.buildPath([ "tree20", "2006", "12", "29", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2006", "12", "30", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2006", "12", "31", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2007", "01", "01", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2007", "01", "02", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2007", "01", "03", ]) in dailyDirs)


   ############################
   # Test writeIndicatorFile()
   ############################

   def testWriteIndicatorFile_001(self):
      """
      Test with a nonexistent staging directory.
      """
      stagingDir = self.buildPath([INVALID_PATH])
      writeIndicatorFile(stagingDir, ENCRYPT_INDICATOR, None, None)   # should just log an error and go on

   def testWriteIndicatorFile_002(self):
      """
      Test with a valid staging directory.
      """
      self.extractTar("tree8")
      stagingDir = self.buildPath(["tree8", "dir001",])
      writeIndicatorFile(stagingDir, ENCRYPT_INDICATOR, None, None)
      self.failUnless(os.path.exists(self.buildPath(["tree8", "dir001", ENCRYPT_INDICATOR,])))


#######################################################################
# Suite definition
#######################################################################

def suite():
   """Returns a suite containing all the test cases in this module."""
   return unittest.TestSuite((
                              unittest.makeSuite(TestFunctions, 'test'),
                            ))


########################################################################
# Module entry point
########################################################################

# When this module is executed from the command-line, run its tests
if __name__ == '__main__':
   unittest.main()
