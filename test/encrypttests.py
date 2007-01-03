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
# Purpose  : Tests encrypt extension functionality.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

########################################################################
# Module documentation
########################################################################

"""
Unit tests for CedarBackup2/extend/encrypt.py.

Code Coverage
=============

   This module contains individual tests for the the public classes implemented
   in extend/encrypt.py.  There are also tests for some of the private
   functions.

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

Testing XML Extraction
======================

   It's difficult to validated that generated XML is exactly "right",
   especially when dealing with pretty-printed XML.  We can't just provide a
   constant string and say "the result must match this".  Instead, what we do
   is extract a node, build some XML from it, and then feed that XML back into
   another object's constructor.  If that parse process succeeds and the old
   object is equal to the new object, we assume that the extract was
   successful.  

   It would arguably be better if we could do a completely independent check -
   but implementing that check would be equivalent to re-implementing all of
   the existing functionality that we're validating here!  After all, the most
   important thing is that data can move seamlessly from object to XML document
   and back to object.

Full vs. Reduced Tests
======================

   Some Cedar Backup regression tests require a specialized environment in
   order to run successfully.  This environment won't necessarily be available
   on every build system out there (for instance, on a Debian autobuilder).
   Because of this, the default behavior is to run a "reduced feature set" test
   suite that has no surprising system, kernel or network requirements.  If you
   want to run all of the tests, set ENCRYPTTESTS_FULL to "Y" in the environment.

   In this module, the primary dependency is that for some tests, GPG must have
   access to the public key for "Kenneth J. Pronovici".  There is also an
   assumption that GPG does I{not} have access to a public key for anyone named
   "Bogus J. User" (so we can test failure scenarios).  

@author Kenneth J. Pronovici <pronovic@ieee.org>
"""


########################################################################
# Import modules and do runtime validations
########################################################################

# System modules
import unittest
import os
import tempfile
import tarfile

# Cedar Backup modules
from CedarBackup2.filesystem import FilesystemList
from CedarBackup2.testutil import findResources, buildPath, removedir, extractTar, failUnlessAssignRaises, platformSupportsLinks
from CedarBackup2.xmlutil import createOutputDom, serializeDom
from CedarBackup2.extend.encrypt import LocalConfig, EncryptConfig
from CedarBackup2.extend.encrypt import _findDailyDirs, _writeIndicator, ENCRYPT_INDICATOR
from CedarBackup2.extend.encrypt import _encryptFileWithGpg, _encryptFile, _encryptDailyDir


#######################################################################
# Module-wide configuration and constants
#######################################################################

DATA_DIRS = [ "./data", "./test/data", ]
RESOURCES = [ "encrypt.conf.1", "encrypt.conf.2", "tree1.tar.gz", "tree2.tar.gz", 
              "tree8.tar.gz", "tree15.tar.gz", "tree16.tar.gz", "tree17.tar.gz",
              "tree18.tar.gz", "tree19.tar.gz", "tree20.tar.gz", ]

VALID_GPG_RECIPIENT = "Kenneth J. Pronovici"
INVALID_GPG_RECIPIENT = "Bogus J. User"

INVALID_PATH = "bogus"  # This path name should never exist


#######################################################################
# Utility functions
#######################################################################

def runAllTests():
   """Returns true/false depending on whether the full test suite should be run."""
   if "ENCRYPTTESTS_FULL" in os.environ:
      return os.environ["ENCRYPTTESTS_FULL"] == "Y"
   else:
      return False


#######################################################################
# Test Case Classes
#######################################################################

##########################
# TestEncryptConfig class
##########################

class TestEncryptConfig(unittest.TestCase):

   """Tests for the EncryptConfig class."""

   ##################
   # Utility methods
   ##################

   def failUnlessAssignRaises(self, exception, object, property, value):
      """Equivalent of L{failUnlessRaises}, but used for property assignments instead."""
      failUnlessAssignRaises(self, exception, object, property, value)


   ############################
   # Test __repr__ and __str__
   ############################

   def testStringFuncs_001(self):
      """
      Just make sure that the string functions don't have errors (i.e. bad variable names).
      """
      obj = EncryptConfig()
      obj.__repr__()
      obj.__str__()


   ##################################
   # Test constructor and attributes
   ##################################

   def testConstructor_001(self):
      """
      Test constructor with no values filled in.
      """
      encrypt = EncryptConfig()
      self.failUnlessEqual(None, encrypt.encryptMode)
      self.failUnlessEqual(None, encrypt.encryptTarget)

   def testConstructor_002(self):
      """
      Test constructor with all values filled in, with valid values.
      """
      encrypt = EncryptConfig("gpg", "Backup User")
      self.failUnlessEqual("gpg", encrypt.encryptMode)
      self.failUnlessEqual("Backup User", encrypt.encryptTarget)

   def testConstructor_003(self):
      """
      Test assignment of encryptMode attribute, None value.
      """
      encrypt = EncryptConfig(encryptMode="gpg")
      self.failUnlessEqual("gpg", encrypt.encryptMode)
      encrypt.encryptMode = None
      self.failUnlessEqual(None, encrypt.encryptMode)

   def testConstructor_004(self):
      """
      Test assignment of encryptMode attribute, valid value.
      """
      encrypt = EncryptConfig()
      self.failUnlessEqual(None, encrypt.encryptMode)
      encrypt.encryptMode = "gpg"
      self.failUnlessEqual("gpg", encrypt.encryptMode)

   def testConstructor_005(self):
      """
      Test assignment of encryptMode attribute, invalid value (empty).
      """
      encrypt = EncryptConfig()
      self.failUnlessEqual(None, encrypt.encryptMode)
      self.failUnlessAssignRaises(ValueError, encrypt, "encryptMode", "")
      self.failUnlessEqual(None, encrypt.encryptMode)

   def testConstructor_006(self):
      """
      Test assignment of encryptTarget attribute, None value.
      """
      encrypt = EncryptConfig(encryptTarget="Backup User")
      self.failUnlessEqual("Backup User", encrypt.encryptTarget)
      encrypt.encryptTarget = None
      self.failUnlessEqual(None, encrypt.encryptTarget)

   def testConstructor_007(self):
      """
      Test assignment of encryptTarget attribute, valid value.
      """
      encrypt = EncryptConfig()
      self.failUnlessEqual(None, encrypt.encryptTarget)
      encrypt.encryptTarget = "Backup User"
      self.failUnlessEqual("Backup User", encrypt.encryptTarget)

   def testConstructor_008(self):
      """
      Test assignment of encryptTarget attribute, invalid value (empty).
      """
      encrypt = EncryptConfig()
      self.failUnlessEqual(None, encrypt.encryptTarget)
      self.failUnlessAssignRaises(ValueError, encrypt, "encryptTarget", "")
      self.failUnlessEqual(None, encrypt.encryptTarget)


   ############################
   # Test comparison operators
   ############################

   def testComparison_001(self):
      """
      Test comparison of two identical objects, all attributes None.
      """
      encrypt1 = EncryptConfig()
      encrypt2 = EncryptConfig()
      self.failUnlessEqual(encrypt1, encrypt2)
      self.failUnless(encrypt1 == encrypt2)
      self.failUnless(not encrypt1 < encrypt2)
      self.failUnless(encrypt1 <= encrypt2)
      self.failUnless(not encrypt1 > encrypt2)
      self.failUnless(encrypt1 >= encrypt2)
      self.failUnless(not encrypt1 != encrypt2)

   def testComparison_002(self):
      """
      Test comparison of two identical objects, all attributes non-None.
      """
      encrypt1 = EncryptConfig("gpg", "Backup User")
      encrypt2 = EncryptConfig("gpg", "Backup User")
      self.failUnlessEqual(encrypt1, encrypt2)
      self.failUnless(encrypt1 == encrypt2)
      self.failUnless(not encrypt1 < encrypt2)
      self.failUnless(encrypt1 <= encrypt2)
      self.failUnless(not encrypt1 > encrypt2)
      self.failUnless(encrypt1 >= encrypt2)
      self.failUnless(not encrypt1 != encrypt2)

   def testComparison_003(self):
      """
      Test comparison of two differing objects, encryptMode differs (one None).
      """
      encrypt1 = EncryptConfig()
      encrypt2 = EncryptConfig(encryptMode="gpg")
      self.failIfEqual(encrypt1, encrypt2)
      self.failUnless(not encrypt1 == encrypt2)
      self.failUnless(encrypt1 < encrypt2)
      self.failUnless(encrypt1 <= encrypt2)
      self.failUnless(not encrypt1 > encrypt2)
      self.failUnless(not encrypt1 >= encrypt2)
      self.failUnless(encrypt1 != encrypt2)

   # Note: no test to check when encrypt mode differs, since only one value is allowed

   def testComparison_004(self):
      """
      Test comparison of two differing objects, encryptTarget differs (one None).
      """
      encrypt1 = EncryptConfig()
      encrypt2 = EncryptConfig(encryptTarget="Backup User")
      self.failIfEqual(encrypt1, encrypt2)
      self.failUnless(not encrypt1 == encrypt2)
      self.failUnless(encrypt1 < encrypt2)
      self.failUnless(encrypt1 <= encrypt2)
      self.failUnless(not encrypt1 > encrypt2)
      self.failUnless(not encrypt1 >= encrypt2)
      self.failUnless(encrypt1 != encrypt2)

   def testComparison_005(self):
      """
      Test comparison of two differing objects, encryptTarget differs.
      """
      encrypt1 = EncryptConfig("gpg", "Another User")
      encrypt2 = EncryptConfig("gpg", "Backup User")
      self.failIfEqual(encrypt1, encrypt2)
      self.failUnless(not encrypt1 == encrypt2)
      self.failUnless(encrypt1 < encrypt2)
      self.failUnless(encrypt1 <= encrypt2)
      self.failUnless(not encrypt1 > encrypt2)
      self.failUnless(not encrypt1 >= encrypt2)
      self.failUnless(encrypt1 != encrypt2)


########################
# TestLocalConfig class
########################

class TestLocalConfig(unittest.TestCase):

   """Tests for the LocalConfig class."""

   ################
   # Setup methods
   ################

   def setUp(self):
      try:
         self.resources = findResources(RESOURCES, DATA_DIRS)
      except Exception, e:
         self.fail(e)

   def tearDown(self):
      pass


   ##################
   # Utility methods
   ##################

   def failUnlessAssignRaises(self, exception, object, property, value):
      """Equivalent of L{failUnlessRaises}, but used for property assignments instead."""
      failUnlessAssignRaises(self, exception, object, property, value)

   def validateAddConfig(self, origConfig):
      """
      Validates that document dumped from C{LocalConfig.addConfig} results in
      identical object.

      We dump a document containing just the encrypt configuration, and then
      make sure that if we push that document back into the C{LocalConfig}
      object, that the resulting object matches the original.

      The C{self.failUnlessEqual} method is used for the validation, so if the
      method call returns normally, everything is OK.

      @param origConfig: Original configuration.
      """
      (xmlDom, parentNode) = createOutputDom()
      origConfig.addConfig(xmlDom, parentNode)
      xmlData = serializeDom(xmlDom)
      newConfig = LocalConfig(xmlData=xmlData, validate=False)
      self.failUnlessEqual(origConfig, newConfig)


   ############################
   # Test __repr__ and __str__
   ############################

   def testStringFuncs_001(self):
      """
      Just make sure that the string functions don't have errors (i.e. bad variable names).
      """
      obj = LocalConfig()
      obj.__repr__()
      obj.__str__()


   #####################################################
   # Test basic constructor and attribute functionality
   #####################################################

   def testConstructor_001(self):
      """
      Test empty constructor, validate=False.
      """
      config = LocalConfig(validate=False)
      self.failUnlessEqual(None, config.encrypt)

   def testConstructor_002(self):
      """
      Test empty constructor, validate=True.
      """
      config = LocalConfig(validate=True)
      self.failUnlessEqual(None, config.encrypt)

   def testConstructor_003(self):
      """
      Test with empty config document as both data and file, validate=False.
      """
      path = self.resources["encrypt.conf.1"]
      contents = open(path).read()
      self.failUnlessRaises(ValueError, LocalConfig, xmlData=contents, xmlPath=path, validate=False)

   def testConstructor_004(self):
      """
      Test assignment of encrypt attribute, None value.
      """
      config = LocalConfig()
      config.encrypt = None
      self.failUnlessEqual(None, config.encrypt)

   def testConstructor_005(self):
      """
      Test assignment of encrypt attribute, valid value.
      """
      config = LocalConfig()
      config.encrypt = EncryptConfig()
      self.failUnlessEqual(EncryptConfig(), config.encrypt)

   def testConstructor_006(self):
      """
      Test assignment of encrypt attribute, invalid value (not EncryptConfig).
      """
      config = LocalConfig()
      self.failUnlessAssignRaises(ValueError, config, "encrypt", "STRING!")


   ############################
   # Test comparison operators
   ############################

   def testComparison_001(self):
      """
      Test comparison of two identical objects, all attributes None.
      """
      config1 = LocalConfig()
      config2 = LocalConfig()
      self.failUnlessEqual(config1, config2)
      self.failUnless(config1 == config2)
      self.failUnless(not config1 < config2)
      self.failUnless(config1 <= config2)
      self.failUnless(not config1 > config2)
      self.failUnless(config1 >= config2)
      self.failUnless(not config1 != config2)

   def testComparison_002(self):
      """
      Test comparison of two identical objects, all attributes non-None.
      """
      config1 = LocalConfig()
      config1.encrypt = EncryptConfig()

      config2 = LocalConfig()
      config2.encrypt = EncryptConfig()

      self.failUnlessEqual(config1, config2)
      self.failUnless(config1 == config2)
      self.failUnless(not config1 < config2)
      self.failUnless(config1 <= config2)
      self.failUnless(not config1 > config2)
      self.failUnless(config1 >= config2)
      self.failUnless(not config1 != config2)

   def testComparison_003(self):
      """
      Test comparison of two differing objects, encrypt differs (one None).
      """
      config1 = LocalConfig()
      config2 = LocalConfig()
      config2.encrypt = EncryptConfig()
      self.failIfEqual(config1, config2)
      self.failUnless(not config1 == config2)
      self.failUnless(config1 < config2)
      self.failUnless(config1 <= config2)
      self.failUnless(not config1 > config2)
      self.failUnless(not config1 >= config2)
      self.failUnless(config1 != config2)

   def testComparison_004(self):
      """
      Test comparison of two differing objects, encrypt differs.
      """
      config1 = LocalConfig()
      config1.encrypt = EncryptConfig(encryptTarget="Another User")

      config2 = LocalConfig()
      config2.encrypt = EncryptConfig(encryptTarget="Backup User")

      self.failIfEqual(config1, config2)
      self.failUnless(not config1 == config2)
      self.failUnless(config1 < config2)
      self.failUnless(config1 <= config2)
      self.failUnless(not config1 > config2)
      self.failUnless(not config1 >= config2)
      self.failUnless(config1 != config2)


   ######################
   # Test validate logic 
   ######################

   def testValidate_001(self):
      """
      Test validate on a None encrypt section.
      """
      config = LocalConfig()
      config.encrypt = None
      self.failUnlessRaises(ValueError, config.validate)

   def testValidate_002(self):
      """
      Test validate on an empty encrypt section.
      """
      config = LocalConfig()
      config.encrypt = EncryptConfig()
      self.failUnlessRaises(ValueError, config.validate)

   def testValidate_003(self):
      """
      Test validate on a non-empty encrypt section with no values filled in.
      """
      config = LocalConfig()
      config.encrypt = EncryptConfig(None, None)
      self.failUnlessRaises(ValueError, config.validate)

   def testValidate_004(self):
      """
      Test validate on a non-empty encrypt section with valid values filled in.
      """
      config = LocalConfig()
      config.encrypt = EncryptConfig("gpg", "Backup User")


   ############################
   # Test parsing of documents
   ############################

   def testParse_001(self):
      """
      Parse empty config document.
      """
      path = self.resources["encrypt.conf.1"]
      contents = open(path).read()
      self.failUnlessRaises(ValueError, LocalConfig, xmlPath=path, validate=True)
      self.failUnlessRaises(ValueError, LocalConfig, xmlData=contents, validate=True)
      config = LocalConfig(xmlPath=path, validate=False)
      self.failUnlessEqual(None, config.encrypt)
      config = LocalConfig(xmlData=contents, validate=False)
      self.failUnlessEqual(None, config.encrypt)

   def testParse_002(self):
      """
      Parse config document with filled-in values.
      """
      path = self.resources["encrypt.conf.2"]
      contents = open(path).read()
      config = LocalConfig(xmlPath=path, validate=False)
      self.failIfEqual(None, config.encrypt)
      self.failUnlessEqual("gpg", config.encrypt.encryptMode)
      self.failUnlessEqual("Backup User", config.encrypt.encryptTarget)
      config = LocalConfig(xmlData=contents, validate=False)
      self.failIfEqual(None, config.encrypt)
      self.failUnlessEqual("gpg", config.encrypt.encryptMode)
      self.failUnlessEqual("Backup User", config.encrypt.encryptTarget)


   ###################
   # Test addConfig()
   ###################

   def testAddConfig_001(self):
      """
      Test with empty config document.
      """
      encrypt = EncryptConfig()
      config = LocalConfig()
      config.encrypt = encrypt
      self.validateAddConfig(config)

   def testAddConfig_002(self):
      """
      Test with values set.
      """
      encrypt = EncryptConfig(encryptMode="gpg", encryptTarget="Backup User")
      config = LocalConfig()
      config.encrypt = encrypt
      self.validateAddConfig(config)


######################
# TestFunctions class
######################

class TestFunctions(unittest.TestCase):

   """Tests for the functions in encrypt.py."""

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


   ########################
   # Test _findDailyDirs()
   ########################

   def testFindDailyDirs_001(self):
      """
      Test with a nonexistent staging directory.
      """
      stagingDir = self.buildPath([INVALID_PATH])
      self.failUnlessRaises(ValueError, _findDailyDirs, stagingDir)

   def testFindDailyDirs_002(self):
      """
      Test with an empty staging directory.
      """
      self.extractTar("tree8")
      stagingDir = self.buildPath(["tree8", "dir001",])
      dailyDirs = _findDailyDirs(stagingDir)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_003(self):
      """
      Test with a staging directory containing only files.
      """
      self.extractTar("tree1")
      stagingDir = self.buildPath(["tree1",])
      dailyDirs = _findDailyDirs(stagingDir)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_004(self):
      """
      Test with a staging directory containing only links.
      """
      self.extractTar("tree15")
      stagingDir = self.buildPath(["tree15", "dir001", ])
      dailyDirs = _findDailyDirs(stagingDir)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_005(self):
      """
      Test with a valid staging directory, where the daily directories do NOT
      contain the encrypt indicator.
      """
      self.extractTar("tree17")  
      stagingDir = self.buildPath(["tree17" ])
      dailyDirs = _findDailyDirs(stagingDir)
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
      dailyDirs = _findDailyDirs(stagingDir)
      self.failUnlessEqual([], dailyDirs)

   def testFindDailyDirs_007(self):
      """
      Test with a valid staging directory, where some daily directories contain
      the encrypt indicator and others do not.
      """
      self.extractTar("tree19")
      stagingDir = self.buildPath(["tree19" ])
      dailyDirs = _findDailyDirs(stagingDir)
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
      dailyDirs = _findDailyDirs(stagingDir)
      self.failUnlessEqual(6, len(dailyDirs))
      self.failUnless(self.buildPath([ "tree20", "2006", "12", "29", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2006", "12", "30", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2006", "12", "31", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2007", "01", "01", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2007", "01", "02", ]) in dailyDirs)
      self.failUnless(self.buildPath([ "tree20", "2007", "01", "03", ]) in dailyDirs)


   #########################
   # Test _writeIndicator()
   #########################

   def testWriteIndicator_001(self):
      """
      Test with a nonexistent staging directory.
      """
      stagingDir = self.buildPath([INVALID_PATH])
      _writeIndicator(stagingDir, None, None)   # should just log an error and go on

   def testWriteIndicator_002(self):
      """
      Test with a valid staging directory.
      """
      self.extractTar("tree8")
      stagingDir = self.buildPath(["tree8", "dir001",])
      _writeIndicator(stagingDir, None, None)
      self.failUnless(os.path.exists(self.buildPath(["tree8", "dir001", ENCRYPT_INDICATOR,])))


   #############################
   # Test _encryptFileWithGpg()
   #############################

   def testEncryptFileWithGpg_001(self):
      """
      Test for a non-existent file in a non-existent directory.
      """
      sourceFile = self.buildPath([INVALID_PATH, INVALID_PATH])
      self.failUnlessRaises(IOError, _encryptFileWithGpg, sourceFile, INVALID_GPG_RECIPIENT)

   def testEncryptFileWithGpg_002(self):
      """
      Test for a non-existent file in an existing directory.
      """
      self.extractTar("tree8")
      sourceFile = self.buildPath(["tree8", "dir001", INVALID_PATH, ])
      self.failUnlessRaises(IOError, _encryptFileWithGpg, sourceFile, INVALID_GPG_RECIPIENT)

   def testEncryptFileWithGpg_003(self):
      """
      Test for an unknown recipient.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      self.failUnlessRaises(IOError, _encryptFileWithGpg, sourceFile, INVALID_GPG_RECIPIENT)
      self.failIf(os.path.exists(expectedFile))
      self.failUnless(os.path.exists(sourceFile))

   def testEncryptFileWithGpg_004(self):
      """
      Test for a valid recipient.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      actualFile = _encryptFileWithGpg(sourceFile, VALID_GPG_RECIPIENT)
      self.failUnlessEqual(actualFile, expectedFile)
      self.failUnless(os.path.exists(sourceFile))
      self.failUnless(os.path.exists(actualFile))


   ######################
   # Test _encryptFile()
   ######################

   def testEncryptFile_001(self):
      """
      Test for a mode other than "gpg".
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      self.failUnlessRaises(ValueError, _encryptFile, sourceFile, "pgp", INVALID_GPG_RECIPIENT, None, None, removeSource=False)
      self.failUnless(os.path.exists(sourceFile))
      self.failIf(os.path.exists(expectedFile))

   def testEncryptFile_002(self):
      """
      Test for a source path that does not exist.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", INVALID_PATH ])
      expectedFile = self.buildPath(["tree1", "%s.gpg" % INVALID_PATH ])
      self.failUnlessRaises(ValueError, _encryptFile, sourceFile, "gpg", INVALID_GPG_RECIPIENT, None, None, removeSource=False)
      self.failIf(os.path.exists(sourceFile))
      self.failIf(os.path.exists(expectedFile))

   def testEncryptFile_003(self):
      """
      Test "gpg" mode with a valid source path and invalid recipient, removeSource=False.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      self.failUnlessRaises(IOError, _encryptFile, sourceFile, "gpg", INVALID_GPG_RECIPIENT, None, None, removeSource=False)
      self.failUnless(os.path.exists(sourceFile))
      self.failIf(os.path.exists(expectedFile))

   def testEncryptFile_004(self):
      """
      Test "gpg" mode with a valid source path and invalid recipient, removeSource=True.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      self.failUnlessRaises(IOError, _encryptFile, sourceFile, "gpg", INVALID_GPG_RECIPIENT, None, None, removeSource=True)
      self.failUnless(os.path.exists(sourceFile))
      self.failIf(os.path.exists(expectedFile))

   def testEncryptFile_005(self):
      """
      Test "gpg" mode with a valid source path and recipient, removeSource=False.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      actualFile = _encryptFile(sourceFile, "gpg", VALID_GPG_RECIPIENT, None, None, removeSource=False)
      self.failUnlessEqual(actualFile, expectedFile)
      self.failUnless(os.path.exists(sourceFile))
      self.failUnless(os.path.exists(actualFile))

   def testEncryptFile_006(self):
      """
      Test "gpg" mode with a valid source path and recipient, removeSource=True.
      """
      self.extractTar("tree1")
      sourceFile = self.buildPath(["tree1", "file001" ])
      expectedFile = self.buildPath(["tree1", "file001.gpg" ])
      actualFile = _encryptFile(sourceFile, "gpg", VALID_GPG_RECIPIENT, None, None, removeSource=True)
      self.failUnlessEqual(actualFile, expectedFile)
      self.failIf(os.path.exists(sourceFile))
      self.failUnless(os.path.exists(actualFile))


   ##########################
   # Test _encryptDailyDir()
   ##########################

   def testEncryptDailyDir_001(self):
      """
      Test with a nonexistent daily staging directory.
      """
      self.extractTar("tree1")
      dailyDir = self.buildPath(["tree1", "dir001" ])
      self.failUnlessRaises(ValueError, _encryptDailyDir, dailyDir, "gpg", VALID_GPG_RECIPIENT, None, None)

   def testEncryptDailyDir_002(self):
      """
      Test with a valid staging directory containing only links.
      """
      if platformSupportsLinks():
         self.extractTar("tree15")
         dailyDir = self.buildPath(["tree15", "dir001" ])
         fsList = FilesystemList()
         fsList.addDirContents(dailyDir)
         self.failUnlessEqual(3, len(fsList))
         self.failUnless(self.buildPath(["tree15", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree15", "dir001", "link001", ]) in fsList)
         self.failUnless(self.buildPath(["tree15", "dir001", "link002", ]) in fsList)
         _encryptDailyDir(dailyDir, "gpg", VALID_GPG_RECIPIENT, None, None)
         fsList = FilesystemList()
         fsList.addDirContents(dailyDir)
         self.failUnlessEqual(3, len(fsList))
         self.failUnless(self.buildPath(["tree15", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree15", "dir001", "link001", ]) in fsList)
         self.failUnless(self.buildPath(["tree15", "dir001", "link002", ]) in fsList)

   def testEncryptDailyDir_003(self):
      """
      Test with a valid staging directory containing only directories.
      """
      self.extractTar("tree2")
      dailyDir = self.buildPath(["tree2"])
      fsList = FilesystemList()
      fsList.addDirContents(dailyDir)
      self.failUnlessEqual(11, len(fsList))
      self.failUnless(self.buildPath(["tree2", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir001", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir002", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir003", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir004", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir005", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir006", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir007", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir008", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir009", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir010", ]) in fsList)
      _encryptDailyDir(dailyDir, "gpg", VALID_GPG_RECIPIENT, None, None)
      fsList = FilesystemList()
      fsList.addDirContents(dailyDir)
      self.failUnlessEqual(11, len(fsList))
      self.failUnless(self.buildPath(["tree2", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir001", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir002", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir003", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir004", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir005", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir006", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir007", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir008", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir009", ]) in fsList)
      self.failUnless(self.buildPath(["tree2", "dir010", ]) in fsList)

   def testEncryptDailyDir_004(self):
      """
      Test with a valid staging directory containing only files.
      """
      self.extractTar("tree1")
      dailyDir = self.buildPath(["tree1"])
      fsList = FilesystemList()
      fsList.addDirContents(dailyDir)
      self.failUnlessEqual(8, len(fsList))
      self.failUnless(self.buildPath(["tree1" ]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file001",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file002",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file003",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file004",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file005",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file006",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file007",]) in fsList)
      _encryptDailyDir(dailyDir, "gpg", VALID_GPG_RECIPIENT, None, None)
      fsList = FilesystemList()
      fsList.addDirContents(dailyDir)
      self.failUnlessEqual(8, len(fsList))
      self.failUnless(self.buildPath(["tree1" ]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file006.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree1", "file007.gpg",]) in fsList)

   def testEncryptDailyDir_005(self):
      """
      Test with a valid staging directory containing files, directories and
      links, including various files that match the general Cedar Backup
      indicator file pattern ("cback.<something>").
      """
      self.extractTar("tree16")
      dailyDir = self.buildPath(["tree16"])
      fsList = FilesystemList()
      fsList.addDirContents(dailyDir)
      if platformSupportsLinks():
         self.failUnlessEqual(122, len(fsList))
         self.failUnless(self.buildPath(["tree16",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "link002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "link002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "link003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "link004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "link005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "cback.",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "link002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "cback.store",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "cback.",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "cback.collect",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "link002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "cback.store",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "link001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "cback.collect",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "cback.stage",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "cback.store",]) in fsList)
      else:
         self.failUnlessEqual(102, len(fsList))
         self.failUnless(self.buildPath(["tree16",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "cback.",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "cback.store",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "cback.",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "cback.collect",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "cback.encrypt",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "cback.store",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file001",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file002",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file003",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file004",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file005",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file006",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file007",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file008",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "cback.collect",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "cback.stage",]) in fsList)
         self.failUnless(self.buildPath(["tree16", "cback.store",]) in fsList)
      _encryptDailyDir(dailyDir, "gpg", VALID_GPG_RECIPIENT, None, None)
      fsList = FilesystemList()
      fsList.addDirContents(dailyDir)
      # since all links are to files, and the files all changed names, the links are invalid and disappear
      self.failUnlessEqual(102, len(fsList))
      self.failUnless(self.buildPath(["tree16",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file006.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file007.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir001", "file008.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir002",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir002", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir003",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir001", "dir003", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir001",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir001", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir002", "dir002", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file006.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file007.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "file008.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir001", "cback.",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir002",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir002", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir003",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir003", "dir003", "cback.store",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file006.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file007.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "file008.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "cback.",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir001", "cback.collect",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir002",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir002", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir003",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir003", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "cback.encrypt",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file006.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file007.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "file008.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir004", "cback.store",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file001.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file002.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file003.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file004.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file005.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file006.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file007.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "dir004", "dir005", "file008.gpg",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "cback.collect",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "cback.stage",]) in fsList)
      self.failUnless(self.buildPath(["tree16", "cback.store",]) in fsList)


#######################################################################
# Suite definition
#######################################################################

def suite():
   """Returns a suite containing all the test cases in this module."""
   if runAllTests():
      return unittest.TestSuite((
                                 unittest.makeSuite(TestEncryptConfig, 'test'), 
                                 unittest.makeSuite(TestLocalConfig, 'test'), 
                                 unittest.makeSuite(TestFunctions, 'test'), 
                               ))
   else:
      return unittest.TestSuite((
                                 unittest.makeSuite(TestEncryptConfig, 'test'), 
                                 unittest.makeSuite(TestLocalConfig, 'test'), 
                                 unittest.makeSuite(TestFunctions, 'testFindDailyDirs'), 
                                 unittest.makeSuite(TestFunctions, 'testWriteIndicator'), 
                               ))


########################################################################
# Module entry point
########################################################################

# When this module is executed from the command-line, run its tests
if __name__ == '__main__':
   unittest.main()
