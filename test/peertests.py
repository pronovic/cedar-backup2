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
# Copyright (c) 2004 Kenneth J. Pronovici.
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
# Purpose  : Tests peer functionality.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# This file was created with a width of 132 characters, and NO tabs.

########################################################################
# Module documentation
########################################################################

"""
Unit tests for CedarBackup2/peer.py.

Code Coverage
=============

   This module contains individual tests for most of the public functions and
   classes implemented in peer.py, including the C{LocalPeer} and C{RemotePeer}
   classes.

   There are some parts of this functionality that can't be tested easily.  For
   instance, the stage code allows the caller to change ownership on files.
   Generally, this can only be done by root, and we won't be running these
   tests as root.  We'll have to hope that the code that tests the way
   permissions are changed gives us enough coverage.

   Network-related testing also causes us problems.  In order to test the
   RemotePeer, we need a "remote" host that we can rcp to and from.  We want to
   fall back on using localhost and the current user, but that might not be
   safe or appropriate.  The compromise is that many of the remote peer tests
   will only be run if PEERTESTS_REMOTE is set to "Y" in the environment.

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

@author Kenneth J. Pronovici <pronovic@ieee.org>
"""


########################################################################
# Import modules and do runtime validations
########################################################################

# Import standard modules
import sys
import os
import stat
import unittest
import tempfile
import tarfile
import getpass
from CedarBackup2.peer import LocalPeer, RemotePeer
from CedarBackup2.peer import DEF_RCP_COMMAND, DEF_COLLECT_INDICATOR, DEF_STAGE_INDICATOR


#######################################################################
# Module-wide configuration and constants
#######################################################################

DATA_DIRS = [ "./data", "./test/data", ]
RESOURCES = [ "tree1.tar.gz", "tree2.tar.gz", "tree9.tar.gz", ]

REMOTE_HOST      = "localhost"                        # Always use login@localhost as our "remote" host
NONEXISTENT_FILE = "bogus"                            # This file name should never exist
NONEXISTENT_HOST = "hostname.invalid"                 # RFC 2606 reserves the ".invalid" TLD for "obviously invalid" names
NONEXISTENT_USER = "unittestuser"                     # This user name should never exist on localhost
NONEXISTENT_CMD  = "/bogus/~~~ZZZZ/bad/not/there"     # This command should never exist in the filesystem


####################
# Utility functions
####################

def findResources():
   """Returns a dictionary of locations for various resources."""
   resources = { }
   for resource in RESOURCES:
      for resourceDir in DATA_DIRS:
         path = os.path.join(resourceDir, resource);
         if os.path.exists(path):
            resources[resource] = path
            break
      else:
         raise Exception("Unable to find resource [%s]." % resource)
   return resources

def extractTar(tmpdir, filepath):
   """Extracts the indicated tar file to self.tmpdir."""
   tar = tarfile.open(filepath)
   for tarinfo in tar:
      tar.extract(tarinfo, tmpdir)

def buildPath(components):
   """Builds a complete path from a list of components."""
   path = components[0]
   for component in components[1:]:
      path = os.path.join(path, component)
   return path

def removedir(tree):
   """Recursively removes an entire directory."""
   for root, dirs, files in os.walk(tree, topdown=False):
      for name in files:
         path = os.path.join(root, name)
         if os.path.islink(path):
            os.remove(path)
         elif os.path.isfile(path):
            os.remove(path)
      for name in dirs:
         path = os.path.join(root, name)
         if os.path.islink(path):
            os.remove(path)
         elif os.path.isdir(path):
            os.rmdir(path)
   os.rmdir(tree)

def remoteExcluded():
   """Returns true/false depending on whether remote tests are excluded."""
   if "PEERTESTS_REMOTE" in os.environ:
      return not os.environ["PEERTESTS_REMOTE"] == "Y"
   else:
      return False

def getMaskAsMode():
   """Returns the user's current umask inverted to a mode."""
   umask = os.umask(0777)
   os.umask(umask)
   return int(~umask & 0777)  # invert, then use only lower bytes 

def getLogin():
   """
   Returns the name of the currently-logged in user.  This might fail under
   some circumstances - but if it does, our tests would fail anyway.
   """
   return getpass.getuser()


#######################################################################
# Test Case Classes
#######################################################################

######################
# TestLocalPeer class
######################

class TestLocalPeer(unittest.TestCase):

   """Tests for the LocalPeer class."""

   ################
   # Setup methods
   ################

   def setUp(self):
      try:
         self.tmpdir = tempfile.mkdtemp()
         self.resources = findResources()
      except Exception, e:
         self.fail(e)

   def tearDown(self):
      removedir(self.tmpdir)


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

   def getFileMode(self, components):
      """Calls buildPath on components and then returns file mode for the file."""
      return stat.S_IMODE(os.stat(self.buildPath(components)).st_mode)


   ###########################
   # Test basic functionality
   ###########################

   def testBasic_001(self):
      """
      Make sure exception is thrown for non-absolute collect directory.
      """
      name = "peer1"
      collectDir = "whatever/something/else/not/absolute"
      self.failUnlessRaises(ValueError, LocalPeer, name, collectDir)

   def testBasic_002(self):
      """
      Make sure attributes are set properly for valid constructor input.
      """
      name = "peer1"
      collectDir = "/absolute/path/name"
      peer = LocalPeer(name, collectDir)
      self.failUnlessEqual(name, peer.name)
      self.failUnlessEqual(collectDir, peer.collectDir)

   def testBasic_003(self):
      """
      Make sure attributes are set properly for valid constructor input, with
      spaces in the collect directory path.
      """
      name = "peer1"
      collectDir = "/ absolute / path/   name "
      peer = LocalPeer(name, collectDir)
      self.failUnlessEqual(name, peer.name)
      self.failUnlessEqual(collectDir, peer.collectDir)


   ###############################
   # Test checkCollectIndicator()
   ###############################

   def testCheckCollectIndicator_001(self):
      """
      Attempt to check collect indicator with non-existent collect directory.
      """
      name = "peer1"
      collectDir = self.buildPath([NONEXISTENT_FILE, ])
      self.failUnless(not os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_002(self):
      """
      Attempt to check collect indicator with non-readable collect directory.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      os.chmod(collectDir, 0200)    # user can't read his own directory
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testCheckCollectIndicator_003(self):
      """
      Attempt to check collect indicator collect indicator file that does not exist.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", DEF_COLLECT_INDICATOR, ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(collectIndicator))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_004(self):
      """
      Attempt to check collect indicator collect indicator file that does not exist, custom name.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", NONEXISTENT_FILE, ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(collectIndicator))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator(collectIndicator=NONEXISTENT_FILE)
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_005(self):
      """
      Attempt to check collect indicator collect indicator file that does exist.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", DEF_COLLECT_INDICATOR, ])
      os.mkdir(collectDir)
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(collectIndicator))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(True, result)

   def testCheckCollectIndicator_006(self):
      """
      Attempt to check collect indicator collect indicator file that does exist, custom name.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", "different", ])
      os.mkdir(collectDir)
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(collectIndicator))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator(collectIndicator="different")
      self.failUnlessEqual(True, result)

   def testCheckCollectIndicator_007(self):
      """
      Attempt to check collect indicator collect indicator file that does exist,
      with spaces in the collect directory path.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect directory here", ])
      collectIndicator = self.buildPath(["collect directory here", DEF_COLLECT_INDICATOR, ])
      os.mkdir(collectDir)
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(collectIndicator))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(True, result)

   def testCheckCollectIndicator_008(self):
      """
      Attempt to check collect indicator collect indicator file that does exist, custom name,
      with spaces in the collect directory path and collect indicator file name.
      """
      name = "peer1"
      collectDir = self.buildPath([" collect dir ", ])
      collectIndicator = self.buildPath([" collect dir ", "different, file", ])
      os.mkdir(collectDir)
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(collectIndicator))
      peer = LocalPeer(name, collectDir)
      result = peer.checkCollectIndicator(collectIndicator="different, file")
      self.failUnlessEqual(True, result)


   #############################
   # Test writeStageIndicator()
   #############################

   def testWriteStageIndicator_001(self):
      """
      Attempt to write stage indicator with non-existent collect directory.
      """
      name = "peer1"
      collectDir = self.buildPath([NONEXISTENT_FILE, ])
      self.failUnless(not os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises(ValueError, peer.writeStageIndicator)

   def testWriteStageIndicator_002(self):
      """
      Attempt to write stage indicator with non-writable collect directory.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      os.chmod(collectDir, 0500)    # read-only for user
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.writeStageIndicator)
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testWriteStageIndicator_003(self):
      """
      Attempt to write stage indicator with non-writable collect directory, custom name.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      os.chmod(collectDir, 0500)    # read-only for user
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.writeStageIndicator, stageIndicator="something")
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testWriteStageIndicator_004(self):
      """
      Attempt to write stage indicator in a valid directory.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      stageIndicator = self.buildPath(["collect", DEF_STAGE_INDICATOR, ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      peer.writeStageIndicator()
      self.failUnless(os.path.exists(stageIndicator))

   def testWriteStageIndicator_005(self):
      """
      Attempt to write stage indicator in a valid directory, custom name.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      stageIndicator = self.buildPath(["collect", "whatever", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      peer.writeStageIndicator(stageIndicator="whatever")
      self.failUnless(os.path.exists(stageIndicator))

   def testWriteStageIndicator_006(self):
      """
      Attempt to write stage indicator in a valid directory, with spaces
      in the directory name.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect from this directory", ])
      stageIndicator = self.buildPath(["collect from this directory", DEF_STAGE_INDICATOR, ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      peer.writeStageIndicator()
      self.failUnless(os.path.exists(stageIndicator))

   def testWriteStageIndicator_007(self):
      """
      Attempt to write stage indicator in a valid directory, custom name,
      with spaces in the directory name and the file name.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect ME", ])
      stageIndicator = self.buildPath(["collect ME", "   whatever-it-takes you", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      peer.writeStageIndicator(stageIndicator="   whatever-it-takes you")
      self.failUnless(os.path.exists(stageIndicator))


   ###################
   # Test stagePeer()
   ###################

   def testStagePeer_001(self):
      """
      Attempt to stage files with non-existent collect directory.
      """
      name = "peer1"
      collectDir = self.buildPath([NONEXISTENT_FILE, ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(targetDir)
      self.failUnless(not os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises(ValueError, peer.stagePeer, targetDir=targetDir)

   def testStagePeer_002(self):
      """
      Attempt to stage files with non-readable collect directory.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      os.chmod(collectDir, 0200)    # user can't read his own directory
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testStagePeer_003(self):
      """
      Attempt to stage files with non-absolute target directory.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      targetDir = "this/is/not/absolute"
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises(ValueError, peer.stagePeer, targetDir=targetDir)

   def testStagePeer_004(self):
      """
      Attempt to stage files with non-existent target directory.
      """
      name = "peer1"
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(targetDir))
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises(ValueError, peer.stagePeer, targetDir=targetDir)

   def testStagePeer_005(self):
      """
      Attempt to stage files with non-writable target directory.
      """
      self.extractTar("tree1")
      name = "peer1"
      collectDir = self.buildPath(["tree1"])
      targetDir = self.buildPath(["target", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      os.chmod(targetDir, 0500)    # read-only for user
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      os.chmod(targetDir, 0777)    # so we can remove it safely
      self.failUnlessEqual(0, len(os.listdir(targetDir)))

   def testStagePeer_006(self):
      """
      Attempt to stage files with empty collect directory.
      @note: This test assumes that scp returns an error if the directory is empty.
      """
      self.extractTar("tree2")
      name = "peer1"
      collectDir = self.buildPath(["tree2", "dir001", ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = LocalPeer(name, collectDir)
      peer.stagePeer(targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual([], stagedFiles)

   def testStagePeer_007(self):
      """
      Attempt to stage files with empty collect directory, where the target
      directory name contains spaces.
      """
      self.extractTar("tree2")
      name = "peer1"
      collectDir = self.buildPath(["tree2", "dir001", ])
      targetDir = self.buildPath([" target directory ", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = LocalPeer(name, collectDir)
      peer.stagePeer(targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual([], stagedFiles)

   def testStagePeer_008(self):
      """
      Attempt to stage files with non-empty collect directory.
      """
      self.extractTar("tree1")
      name = "peer1"
      collectDir = self.buildPath(["tree1", ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = LocalPeer(name, collectDir)
      peer.stagePeer(targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(7, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)
      self.failUnless("file003" in stagedFiles)
      self.failUnless("file004" in stagedFiles)
      self.failUnless("file005" in stagedFiles)
      self.failUnless("file006" in stagedFiles)
      self.failUnless("file007" in stagedFiles)

   def testStagePeer_009(self):
      """
      Attempt to stage files with non-empty collect directory, where the
      target directory name contains spaces.
      """
      self.extractTar("tree1")
      name = "peer1"
      collectDir = self.buildPath(["tree1", ])
      targetDir = self.buildPath(["target directory place", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = LocalPeer(name, collectDir)
      peer.stagePeer(targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(7, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)
      self.failUnless("file003" in stagedFiles)
      self.failUnless("file004" in stagedFiles)
      self.failUnless("file005" in stagedFiles)
      self.failUnless("file006" in stagedFiles)
      self.failUnless("file007" in stagedFiles)

   def testStagePeer_010(self):
      """
      Attempt to stage files with non-empty collect directory containing links and directories.
      """
      self.extractTar("tree9")
      name = "peer1"
      collectDir = self.buildPath(["tree9", ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = LocalPeer(name, collectDir)
      self.failUnlessRaises(ValueError, peer.stagePeer, targetDir=targetDir)

   def testStagePeer_011(self):
      """
      Attempt to stage files with non-empty collect directory and attempt to set valid permissions.
      """
      self.extractTar("tree1")
      name = "peer1"
      collectDir = self.buildPath(["tree1", ])
      targetDir = self.buildPath(["target", ])
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = LocalPeer(name, collectDir)
      if getMaskAsMode() == 0400:
         permissions = 0642   # arbitrary, but different than umask would give
      else:
         permissions = 0400   # arbitrary
      peer.stagePeer(targetDir=targetDir, permissions=permissions)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(7, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)
      self.failUnless("file003" in stagedFiles)
      self.failUnless("file004" in stagedFiles)
      self.failUnless("file005" in stagedFiles)
      self.failUnless("file006" in stagedFiles)
      self.failUnless("file007" in stagedFiles)
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file001", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file002", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file003", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file004", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file005", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file006", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file007", ]))


######################
# TestRemotePeer class
######################

class TestRemotePeer(unittest.TestCase):

   """Tests for the RemotePeer class."""

   ################
   # Setup methods
   ################

   def setUp(self):
      try:
         self.tmpdir = tempfile.mkdtemp()
         self.resources = findResources()
      except Exception, e:
         self.fail(e)

   def tearDown(self):
      removedir(self.tmpdir)


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

   def getFileMode(self, components):
      """Calls buildPath on components and then returns file mode for the file."""
      return stat.S_IMODE(os.stat(self.buildPath(components)).st_mode)


   ############################
   # Tests basic functionality
   ############################

   def testBasic_001(self):
      """
      Make sure exception is thrown for non-absolute collect directory.
      """
      name = REMOTE_HOST
      collectDir = "whatever/something/else/not/absolute"
      remoteUser = getLogin()
      self.failUnlessRaises(ValueError, RemotePeer, name, remoteUser, collectDir)

   def testBasic_002(self):
      """
      Make sure attributes are set properly for valid constructor input.
      """
      name = REMOTE_HOST
      collectDir = "/absolute/path/name"
      remoteUser = getLogin()
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessEqual(name, peer.name)
      self.failUnlessEqual(collectDir, peer.collectDir)
      self.failUnlessEqual(remoteUser, peer.remoteUser)
      self.failUnlessEqual(DEF_RCP_COMMAND, peer.rcpCommand)

   def testBasic_003(self):
      """
      Make sure attributes are set properly for valid constructor input, where
      the collect directory contains spaces.
      """
      name = REMOTE_HOST
      collectDir = "/absolute/path/to/ a large directory"
      remoteUser = getLogin()
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessEqual(name, peer.name)
      self.failUnlessEqual(collectDir, peer.collectDir)
      self.failUnlessEqual(remoteUser, peer.remoteUser)
      self.failUnlessEqual(DEF_RCP_COMMAND, peer.rcpCommand)

   def testBasic_004(self):
      """
      Make sure attributes are set properly for valid constructor input, custom rcp command.
      """
      name = REMOTE_HOST
      collectDir = "/absolute/path/name"
      remoteUser = getLogin()
      rcpCommand = "rcp -one --two three \"four five\" 'six seven' eight"
      peer = RemotePeer(name, remoteUser, collectDir, rcpCommand)
      self.failUnlessEqual(name, peer.name)
      self.failUnlessEqual(collectDir, peer.collectDir)
      self.failUnlessEqual(remoteUser, peer.remoteUser)
      self.failUnlessEqual(["rcp", "-one", "--two", "three", "four five", "'six", "seven'", "eight", ], peer.rcpCommand)


   ###############################
   # Test checkCollectIndicator()
   ###############################

   def testCheckCollectIndicator_001(self):
      """
      Attempt to check collect indicator with invalid hostname.
      """
      name = NONEXISTENT_HOST
      collectDir = self.buildPath(["collect", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      remoteUser = getLogin()
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_002(self):
      """
      Attempt to check collect indicator with invalid remote user.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = NONEXISTENT_USER
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_003(self):
      """
      Attempt to check collect indicator with invalid rcp command.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = getLogin()
      rcpCommand = NONEXISTENT_CMD
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir, rcpCommand)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_004(self):
      """
      Attempt to check collect indicator with non-existent collect directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = getLogin()
      self.failUnless(not os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_005(self):
      """
      Attempt to check collect indicator with non-readable collect directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      os.chmod(collectDir, 0200)    # user can't read his own directory
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testCheckCollectIndicator_006(self):
      """
      Attempt to check collect indicator collect indicator file that does not exist.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", DEF_COLLECT_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_007(self):
      """
      Attempt to check collect indicator collect indicator file that does not exist, custom name.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", NONEXISTENT_FILE, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_008(self):
      """
      Attempt to check collect indicator collect indicator file that does not
      exist, where the collect directory contains spaces.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect directory path", ])
      collectIndicator = self.buildPath(["collect directory path", DEF_COLLECT_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_009(self):
      """
      Attempt to check collect indicator collect indicator file that does not
      exist, custom name, where the collect directory contains spaces.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["  you collect here   ", ])
      collectIndicator = self.buildPath(["  you collect here   ", NONEXISTENT_FILE, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(False, result)

   def testCheckCollectIndicator_010(self):
      """
      Attempt to check collect indicator collect indicator file that does exist.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", DEF_COLLECT_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(True, result)

   def testCheckCollectIndicator_011(self):
      """
      Attempt to check collect indicator collect indicator file that does exist, custom name.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      collectIndicator = self.buildPath(["collect", "whatever", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator(collectIndicator="whatever")
      self.failUnlessEqual(True, result)

   def testCheckCollectIndicator_012(self):
      """
      Attempt to check collect indicator collect indicator file that does exist,
      where the collect directory contains spaces.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect NOT", ])
      collectIndicator = self.buildPath(["collect NOT", DEF_COLLECT_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator()
      self.failUnlessEqual(True, result)

   def testCheckCollectIndicator_013(self):
      """
      Attempt to check collect indicator collect indicator file that does
      exist, custom name, where the collect directory and indicator file
      contain spaces.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath([" from here collect!", ])
      collectIndicator = self.buildPath([" from here collect!", "whatever, dude", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      open(collectIndicator, "w").write("")     # touch the file
      self.failUnless(os.path.exists(collectIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      result = peer.checkCollectIndicator(collectIndicator="whatever, dude")
      self.failUnlessEqual(True, result)


   #############################
   # Test writeStageIndicator()
   #############################

   def testWriteStageIndicator_001(self):
      """
      Attempt to write stage indicator with invalid hostname.
      """
      name = NONEXISTENT_HOST
      collectDir = self.buildPath(["collect", ])
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      remoteUser = getLogin()
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.writeStageIndicator)

   def testWriteStageIndicator_002(self):
      """
      Attempt to write stage indicator with invalid remote user.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = NONEXISTENT_USER
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.writeStageIndicator)

   def testWriteStageIndicator_003(self):
      """
      Attempt to write stage indicator with invalid rcp command.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = getLogin()
      rcpCommand = NONEXISTENT_CMD
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir, rcpCommand)
      self.failUnlessRaises((IOError,OSError), peer.writeStageIndicator)

   def testWriteStageIndicator_004(self):
      """
      Attempt to write stage indicator with non-existent collect directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      remoteUser = getLogin()
      self.failUnless(not os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises(ValueError, peer.writeStageIndicator)

   def testWriteStageIndicator_005(self):
      """
      Attempt to write stage indicator with non-writable collect directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      stageIndicator = self.buildPath(["collect", DEF_STAGE_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(stageIndicator))
      os.chmod(collectDir, 0400)    # read-only for user
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.writeStageIndicator)
      self.failUnless(not os.path.exists(stageIndicator))
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testWriteStageIndicator_006(self):
      """
      Attempt to write stage indicator in a valid directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      stageIndicator = self.buildPath(["collect", DEF_STAGE_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(stageIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      peer.writeStageIndicator()
      self.failUnless(os.path.exists(stageIndicator))

   def testWriteStageIndicator_007(self):
      """
      Attempt to write stage indicator in a valid directory, custom name.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      stageIndicator = self.buildPath(["collect", "newname", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(stageIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      peer.writeStageIndicator(stageIndicator="newname")
      self.failUnless(os.path.exists(stageIndicator))

   def testWriteStageIndicator_008(self):
      """
      Attempt to write stage indicator in a valid directory that contains
      spaces.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["with spaces collect", ])
      stageIndicator = self.buildPath(["with spaces collect", DEF_STAGE_INDICATOR, ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(stageIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      peer.writeStageIndicator()
      self.failUnless(os.path.exists(stageIndicator))

   def testWriteStageIndicator_009(self):
      """
      Attempt to write stage indicator in a valid directory, custom name, where
      the collect directory and the custom name contain spaces.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect, soon", ])
      stageIndicator = self.buildPath(["collect, soon", "new name with spaces", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(stageIndicator))
      peer = RemotePeer(name, remoteUser, collectDir)
      peer.writeStageIndicator(stageIndicator="new name with spaces")
      self.failUnless(os.path.exists(stageIndicator))


   ###################
   # Test stagePeer()
   ###################

   def testStagePeer_001(self):
      """
      Attempt to stage files with invalid hostname.
      """
      name = NONEXISTENT_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)

   def testStagePeer_002(self):
      """
      Attempt to stage files with invalid remote user.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = NONEXISTENT_USER
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)

   def testStagePeer_003(self):
      """
      Attempt to stage files with invalid rcp command.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      rcpCommand = NONEXISTENT_CMD
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir, rcpCommand)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)

   def testStagePeer_004(self):
      """
      Attempt to stage files with non-existent collect directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(targetDir)
      self.failUnless(not os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)

   def testStagePeer_005(self):
      """
      Attempt to stage files with non-readable collect directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      os.chmod(collectDir, 0200)    # user can't read his own directory
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      os.chmod(collectDir, 0777)    # so we can remove it safely

   def testStagePeer_006(self):
      """
      Attempt to stage files with non-absolute target directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = "non/absolute/target"
      remoteUser = getLogin()
      self.failUnless(not os.path.exists(collectDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises(ValueError, peer.stagePeer, targetDir=targetDir)

   def testStagePeer_007(self):
      """
      Attempt to stage files with non-existent target directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(not os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises(ValueError, peer.stagePeer, targetDir=targetDir)

   def testStagePeer_008(self):
      """
      Attempt to stage files with non-writable target directory.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      os.chmod(targetDir, 0400)    # read-only for user
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      os.chmod(collectDir, 0777)    # so we can remove it safely
      self.failUnlessEqual(0, len(os.listdir(targetDir)))

   def testStagePeer_009(self):
      """
      Attempt to stage files with empty collect directory.
      @note: This test assumes that scp returns an error if the directory is empty.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual([], stagedFiles)

   def testStagePeer_010(self):
      """
      Attempt to stage files with empty collect directory, with a target
      directory that contains spaces.
      @note: This test assumes that scp returns an error if the directory is empty.
      """
      name = REMOTE_HOST
      collectDir = self.buildPath(["collect", ])
      targetDir = self.buildPath(["target DIR", ])
      remoteUser = getLogin()
      os.mkdir(collectDir)
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual([], stagedFiles)

   def testStagePeer_011(self):
      """
      Attempt to stage files with non-empty collect directory.
      """
      self.extractTar("tree1")
      name = REMOTE_HOST
      collectDir = self.buildPath(["tree1", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = RemotePeer(name, remoteUser, collectDir)
      peer.stagePeer(targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(7, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)
      self.failUnless("file003" in stagedFiles)
      self.failUnless("file004" in stagedFiles)
      self.failUnless("file005" in stagedFiles)
      self.failUnless("file006" in stagedFiles)
      self.failUnless("file007" in stagedFiles)

   def testStagePeer_012(self):
      """
      Attempt to stage files with non-empty collect directory, with a target
      directory that contains spaces.
      """
      self.extractTar("tree1")
      name = REMOTE_HOST
      collectDir = self.buildPath(["tree1", ])
      targetDir = self.buildPath(["write the target here, now!", ])
      remoteUser = getLogin()
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = RemotePeer(name, remoteUser, collectDir)
      peer.stagePeer(targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(7, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)
      self.failUnless("file003" in stagedFiles)
      self.failUnless("file004" in stagedFiles)
      self.failUnless("file005" in stagedFiles)
      self.failUnless("file006" in stagedFiles)
      self.failUnless("file007" in stagedFiles)

   def testStagePeer_013(self):
      """
      Attempt to stage files with non-empty collect directory containing links and directories.
      @note: We assume that scp copies the files even though it returns an error due to directories.
      """
      self.extractTar("tree9")
      name = REMOTE_HOST
      collectDir = self.buildPath(["tree9", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = RemotePeer(name, remoteUser, collectDir)
      self.failUnlessRaises((IOError,OSError), peer.stagePeer, targetDir=targetDir)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(2, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)

   def testStagePeer_014(self):
      """
      Attempt to stage files with non-empty collect directory and attempt to set valid permissions.
      """
      self.extractTar("tree1")
      name = REMOTE_HOST
      collectDir = self.buildPath(["tree1", ])
      targetDir = self.buildPath(["target", ])
      remoteUser = getLogin()
      os.mkdir(targetDir)
      self.failUnless(os.path.exists(collectDir))
      self.failUnless(os.path.exists(targetDir))
      self.failUnlessEqual(0, len(os.listdir(targetDir)))
      peer = RemotePeer(name, remoteUser, collectDir)
      if getMaskAsMode() == 0400:
         permissions = 0642   # arbitrary, but different than umask would give
      else:
         permissions = 0400   # arbitrary
      peer.stagePeer(targetDir=targetDir, permissions=permissions)
      stagedFiles = os.listdir(targetDir)
      self.failUnlessEqual(7, len(stagedFiles))
      self.failUnless("file001" in stagedFiles)
      self.failUnless("file002" in stagedFiles)
      self.failUnless("file003" in stagedFiles)
      self.failUnless("file004" in stagedFiles)
      self.failUnless("file005" in stagedFiles)
      self.failUnless("file006" in stagedFiles)
      self.failUnless("file007" in stagedFiles)
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file001", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file002", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file003", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file004", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file005", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file006", ]))
      self.failUnlessEqual(permissions, self.getFileMode(["target", "file007", ]))


#######################################################################
# Suite definition
#######################################################################

def suite():
   """Returns a suite containing all the test cases in this module."""
   if remoteExcluded():
      return unittest.TestSuite((
                                 unittest.makeSuite(TestLocalPeer, 'test'),
                                 unittest.makeSuite(TestRemotePeer, 'testBasic'), 
                               ))
   else:
      return unittest.TestSuite((
                                 unittest.makeSuite(TestLocalPeer, 'test'),
                                 unittest.makeSuite(TestRemotePeer, 'test'), 
                               ))


########################################################################
# Module entry point
########################################################################

# When this module is executed from the command-line, run its tests
if __name__ == '__main__':
   unittest.main()
