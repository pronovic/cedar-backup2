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
# Purpose  : Provides backup peer-related objects.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# This file was created with a width of 132 characters, and NO tabs.

########################################################################
# Module documentation
########################################################################

"""
Provides backup peer-related objects and utility functions.

@sort: LocalPeer, Remote Peer

@var DEF_COLLECT_INDICATOR: Name of the default collect indicator file.
@var DEF_STAGE_INDICATOR: Name of the default stage indicator file.

@author: Kenneth J. Pronovici <pronovic@ieee.org>
"""


########################################################################
# Imported modules
########################################################################

# System modules
import os
import logging
import shutil
import tempfile
import sets
import re

# Cedar Backup modules
from CedarBackup2.filesystem import FilesystemList
from CedarBackup2.util import splitCommandLine, executeCommand, encodePath


########################################################################
# Module-wide constants and variables
########################################################################

logger                  = logging.getLogger("CedarBackup2.log.peer")

DEF_RCP_COMMAND         = [ "/usr/bin/scp", "-B", "-q", "-C" ]
DEF_COLLECT_INDICATOR   = "cback.collect"
DEF_STAGE_INDICATOR     = "cback.stage"

SU_COMMAND              = [ "su" ]


########################################################################
# LocalPeer class definition
########################################################################

class LocalPeer(object):

   ######################
   # Class documentation
   ######################

   """
   Backup peer representing a local peer in a backup pool.

   This is a class representing a local (non-network) peer in a backup pool.
   Local peers are backed up by simple filesystem copy operations.  A local
   peer has associated with it a name (typically, but not necessarily, a
   hostname) and a collect directory.

   The public methods other than the constructor are part of a "backup peer"
   interface shared with the C{RemotePeer} class.

   @sort: __init__, stagePeer, checkCollectIndicator, writeStageIndicator, 
          _copyLocalDir, _copyLocalFile, name, collectDir
   """

   ##############
   # Constructor
   ##############

   def __init__(self, name, collectDir):
      """
      Initializes a local backup peer.

      Note that the collect directory must be an absolute path, but does not
      have to exist when the object is instantiated.  We do a lazy validation
      on this value since we could (potentially) be creating peer objects
      before an ongoing backup completed.
      
      @param name: Name of the backup peer
      @type name: String, typically a hostname

      @param collectDir: Path to the peer's collect directory 
      @type collectDir: String representing an absolute local path on disk

      @raise ValueError: If the name is empty.
      @raise ValueError: If collect directory is not an absolute path.
      """
      self._name = None
      self._collectDir = None
      self.name = name
      self.collectDir = collectDir


   #############
   # Properties
   #############

   def _setName(self, value):
      """
      Property target used to set the peer name.
      The value must be a non-empty string and cannot be C{None}.
      @raise ValueError: If the value is an empty string or C{None}.
      """
      if value is None or len(value) < 1:
         raise ValueError("Peer name must be a non-empty string.")
      self._name = value

   def _getName(self):
      """
      Property target used to get the peer name.
      """
      return self._name

   def _setCollectDir(self, value):
      """
      Property target used to set the collect directory.
      The value must be an absolute path and cannot be C{None}.
      It does not have to exist on disk at the time of assignment.
      @raise ValueError: If the value is C{None} or is not an absolute path.
      @raise ValueError: If a path cannot be encoded properly.
      """
      if value is None or not os.path.isabs(value):
         raise ValueError("Collect directory must be an absolute path.")
      self._collectDir = encodePath(value)

   def _getCollectDir(self):
      """
      Property target used to get the collect directory.
      """
      return self._collectDir

   name = property(_getName, _setName, None, "Name of the peer.")
   collectDir = property(_getCollectDir, _setCollectDir, None, "Path to the peer's collect directory (an absolute local path).")


   #################
   # Public methods
   #################

   def stagePeer(self, targetDir, ownership=None, permissions=None):
      """
      Stages data from the peer into the indicated local target directory.

      The collect and target directories must both already exist before this
      method is called.  If passed in, ownership and permissions will be
      applied to the files that are copied.
   
      @note: The caller is responsible for checking that the indicator exists,
      if they care.  This function only stages the files within the directory.

      @note: If you have user/group as strings, call the L{util.getUidGid} function
      to get the associated uid/gid as an ownership tuple.

      @param targetDir: Target directory to write data into
      @type targetDir: String representing a directory on disk

      @param ownership: Owner and group that the staged files should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the staged files should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @return: Number of files copied from the source directory to the target directory.

      @raise ValueError: If collect directory is not a directory or does not exist 
      @raise ValueError: If target directory is not a directory, does not exist or is not absolute.
      @raise ValueError: If a path cannot be encoded properly.
      @raise IOError: If there were no files to stage (i.e. the directory was empty)
      @raise IOError: If there is an IO error copying a file.
      @raise OSError: If there is an OS error copying or changing permissions on a file
      """
      targetDir = encodePath(targetDir)
      if not os.path.isabs(targetDir):
         logger.debug("Target directory [%s] not an absolute path." % targetDir)
         raise ValueError("Target directory must be an absolute path.")
      if not os.path.exists(self.collectDir) or not os.path.isdir(self.collectDir):
         logger.debug("Collect directory [%s] is not a directory or does not exist on disk." % self.collectDir)
         raise ValueError("Collect directory is not a directory or does not exist on disk.")
      if not os.path.exists(targetDir) or not os.path.isdir(targetDir):
         logger.debug("Target directory [%s] is not a directory or does not exist on disk." % targetDir)
         raise ValueError("Target directory is not a directory or does not exist on disk.")
      count = LocalPeer._copyLocalDir(self.collectDir, targetDir, ownership, permissions)
      if count == 0:
         raise IOError("Did not copy any files from local peer.")
      return count

   def checkCollectIndicator(self, collectIndicator=None):
      """
      Checks the collect indicator in the peer's staging directory.

      When a peer has completed collecting its backup files, it will write an
      empty indicator file into its collect directory.  This method checks to
      see whether that indicator has been written.  We're "stupid" here - if
      the collect directory doesn't exist, you'll naturally get back C{False}.

      If you need to, you can override the name of the collect indicator file
      by passing in a different name.

      @param collectIndicator: Name of the collect indicator file to check
      @type collectIndicator: String representing name of a file in the collect directory

      @return: Boolean true/false depending on whether the indicator exists.
      @raise ValueError: If a path cannot be encoded properly.
      """
      collectIndicator = encodePath(collectIndicator)
      if collectIndicator is None:
         return os.path.exists(os.path.join(self.collectDir, DEF_COLLECT_INDICATOR))
      else:
         return os.path.exists(os.path.join(self.collectDir, collectIndicator))

   def writeStageIndicator(self, stageIndicator=None, ownership=None, permissions=None):
      """
      Writes the stage indicator in the peer's staging directory.

      When the master has completed collecting its backup files, it will write
      an empty indicator file into the peer's collect directory.  The presence
      of this file implies that the staging process is complete.

      If you need to, you can override the name of the stage indicator file by
      passing in a different name.

      @note: If you have user/group as strings, call the L{util.getUidGid}
      function to get the associated uid/gid as an ownership tuple.

      @param stageIndicator: Name of the indicator file to write
      @type stageIndicator: String representing name of a file in the collect directory

      @param ownership: Owner and group that the indicator file should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the indicator file should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @raise ValueError: If collect directory is not a directory or does not exist 
      @raise ValueError: If a path cannot be encoded properly.
      @raise IOError: If there is an IO error creating the file.
      @raise OSError: If there is an OS error creating or changing permissions on the file
      """
      stageIndicator = encodePath(stageIndicator)
      if not os.path.exists(self.collectDir) or not os.path.isdir(self.collectDir):
         logger.debug("Collect directory [%s] is not a directory or does not exist on disk." % self.collectDir)
         raise ValueError("Collect directory is not a directory or does not exist on disk.")
      if stageIndicator is None:
         fileName = os.path.join(self.collectDir, DEF_STAGE_INDICATOR)
      else:
         fileName = os.path.join(self.collectDir, stageIndicator)
      LocalPeer._copyLocalFile(None, fileName, ownership, permissions)    # None for sourceFile results in an empty target


   ##################
   # Private methods
   ##################

   def _copyLocalDir(sourceDir, targetDir, ownership=None, permissions=None):
      """
      Copies files from the source directory to the target directory.

      This function is not recursive.  Only the files in the directory will be
      copied.   Ownership and permissions will be left at their default values
      if new values are not specified.  The source and target directories are
      allowed to be soft links to a directory, but besides that soft links are
      ignored.

      @note: If you have user/group as strings, call the L{util.getUidGid}
      function to get the associated uid/gid as an ownership tuple.

      @param sourceDir: Source directory
      @type sourceDir: String representing a directory on disk

      @param targetDir: Target directory
      @type targetDir: String representing a directory on disk

      @param ownership: Owner and group that the copied files should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the staged files should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @return: Number of files copied from the source directory to the target directory.

      @raise ValueError: If source or target is not a directory or does not exist.
      @raise ValueError: If a path cannot be encoded properly.
      @raise IOError: If there is an IO error copying the files.
      @raise OSError: If there is an OS error copying or changing permissions on a files
      """
      filesCopied = 0
      sourceDir = encodePath(sourceDir)
      targetDir = encodePath(targetDir)
      for fileName in os.listdir(sourceDir):
         sourceFile = os.path.join(sourceDir, fileName)
         targetFile = os.path.join(targetDir, fileName)
         LocalPeer._copyLocalFile(sourceFile, targetFile, ownership, permissions)
         filesCopied += 1
      return filesCopied
   _copyLocalDir = staticmethod(_copyLocalDir)

   def _copyLocalFile(sourceFile=None, targetFile=None, ownership=None, permissions=None, overwrite=True):
      """
      Copies a source file to a target file.

      If the source file is C{None} then the target file will be created or
      overwritten as an empty file.  If the target file is C{None}, this method
      is a no-op.  Attempting to copy a soft link or a directory will result in
      an exception.

      @note: If you have user/group as strings, call the L{util.getUidGid}
      function to get the associated uid/gid as an ownership tuple.

      @note: We will not overwrite a target file that exists when this method
      is invoked.  If the target already exists, we'll raise an exception.

      @param sourceFile: Source file to copy
      @type sourceFile: String representing a file on disk, as an absolute path

      @param targetFile: Target file to create
      @type targetFile: String representing a file on disk, as an absolute path

      @param ownership: Owner and group that the copied should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the staged files should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @param overwrite: Indicates whether it's OK to overwrite the target file.
      @type overwrite: Boolean true/false.

      @raise ValueError: If the passed-in source file is not a regular file.
      @raise ValueError: If a path cannot be encoded properly.
      @raise IOError: If the target file already exists.
      @raise IOError: If there is an IO error copying the file
      @raise OSError: If there is an OS error copying or changing permissions on a file
      """
      targetFile = encodePath(targetFile)
      sourceFile = encodePath(sourceFile)
      if targetFile is None:
         return
      if not overwrite:
         if os.path.exists(targetFile):
            raise IOError("Target file [%s] already exists." % targetFile)
      if sourceFile is None:
         open(targetFile, "w").write("")
      else:
         if os.path.isfile(sourceFile) and not os.path.islink(sourceFile):
            shutil.copy(sourceFile, targetFile)
         else:
            logger.debug("Source [%s] is not a regular file." % sourceFile)
            raise ValueError("Source is not a regular file.")
      if ownership is not None:
         os.chown(targetFile, ownership[0], ownership[1])
      if permissions is not None:
         os.chmod(targetFile, permissions)
   _copyLocalFile = staticmethod(_copyLocalFile)


########################################################################
# RemotePeer class definition
########################################################################

class RemotePeer(object):

   ######################
   # Class documentation
   ######################

   """
   Backup peer representing a remote peer in a backup pool.

   This is a class representing a remote (networked) peer in a backup pool.
   Remote peers are backed up using an rcp-compatible copy command.  A remote
   peer has associated with it a name (which must be a valid hostname), a
   collect directory, a working directory and a copy method (an rcp-compatible
   command).  

   You can also set an optional local user value.  This username will be used
   as the local user for any remote copies that are required.  It can only be
   used if the root user is executing the backup.  The root user will C{su} to
   the local user and execute the remote copies as that user.

   The copy method is associated with the peer and not with the actual request
   to copy, because we can envision that each remote host might have a
   different connect method.

   The public methods other than the constructor are part of a "backup peer"
   interface shared with the C{LocalPeer} class.

   @sort: __init__, stagePeer, checkCollectIndicator, writeStageIndicator, 
          _getDirContents, _copyRemoteDir, _copyRemoteFile, _pushLocalFile, 
          name, collectDir, remoteUser, rcpCommand
   """

   ##############
   # Constructor
   ##############

   def __init__(self, name, collectDir, workingDir, remoteUser, rcpCommand=None, localUser=None):
      """
      Initializes a remote backup peer.

      @note: If provided, the rcp command will eventually be parsed into a list
      of strings suitable for passing to L{popen2.Popen4} in order to avoid
      security holes related to shell interpolation.   This parsing will be
      done by the L{util.splitCommandLine} function.  See the documentation for
      that function for some important notes about its limitations.

      @param name: Name of the backup peer
      @type name: String, must be a valid DNS hostname

      @param collectDir: Path to the peer's collect directory 
      @type collectDir: String representing an absolute path on the remote peer

      @param workingDir: Working directory that can be used to create temporary files, etc.
      @type workingDir: String representing an absolute path on the current host.
      
      @param remoteUser: Name of the Cedar Backup user on the remote peer
      @type remoteUser: String representing a username, valid via the copy command

      @param rcpCommand: An rcp-compatible copy command to use for copying files from the peer
      @type rcpCommand: String representing a system command including required arguments

      @param localUser: Name of the Cedar Backup user on the current host
      @type localUser: String representing a username, valid on the current host

      @raise ValueError: If collect directory is not an absolute path
      """
      self._name = None
      self._collectDir = None
      self._workingDir = None
      self._remoteUser = None
      self._localUser = None
      self._rcpCommand = None
      self._rcpCommandList = None
      self.name = name
      self.collectDir = collectDir
      self.workingDir = workingDir
      self.remoteUser = remoteUser
      self.localUser = localUser
      self.rcpCommand = rcpCommand


   #############
   # Properties
   #############

   def _setName(self, value):
      """
      Property target used to set the peer name.
      The value must be a non-empty string and cannot be C{None}.
      @raise ValueError: If the value is an empty string or C{None}.
      """
      if value is None or len(value) < 1:
         raise ValueError("Peer name must be a non-empty string.")
      self._name = value

   def _getName(self):
      """
      Property target used to get the peer name.
      """
      return self._name

   def _setCollectDir(self, value):
      """
      Property target used to set the collect directory.
      The value must be an absolute path and cannot be C{None}.
      It does not have to exist on disk at the time of assignment.
      @raise ValueError: If the value is C{None} or is not an absolute path.
      @raise ValueError: If the value cannot be encoded properly.
      """
      if value is None or not os.path.isabs(value):
         raise ValueError("Collect directory must be an absolute path.")
      self._collectDir = encodePath(value)

   def _getCollectDir(self):
      """
      Property target used to get the collect directory.
      """
      return self._collectDir

   def _setWorkingDir(self, value):
      """
      Property target used to set the working directory.
      The value must be an absolute path and cannot be C{None}.
      @raise ValueError: If the value is C{None} or is not an absolute path.
      @raise ValueError: If the value cannot be encoded properly.
      """
      if value is None or not os.path.isabs(value):
         raise ValueError("Working directory must be an absolute path.")
      self._workingDir = encodePath(value)

   def _getWorkingDir(self):
      """
      Property target used to get the working directory.
      """
      return self._workingDir

   def _setRemoteUser(self, value):
      """
      Property target used to set the remote user.
      The value must be a non-empty string and cannot be C{None}.
      @raise ValueError: If the value is an empty string or C{None}.
      """
      if value is None or len(value) < 1:
         raise ValueError("Peer remote user must be a non-empty string.")
      self._remoteUser = value

   def _getRemoteUser(self):
      """
      Property target used to get the remote user.
      """
      return self._remoteUser

   def _setLocalUser(self, value):
      """
      Property target used to set the local user.
      The value must be a non-empty string if it is not C{None}.
      @raise ValueError: If the value is an empty string.
      """
      if value is not None:
         if len(value) < 1:
            raise ValueError("Peer local user must be a non-empty string.")
      self._localUser = value

   def _getLocalUser(self):
      """
      Property target used to get the local user.
      """
      return self._localUser

   def _setRcpCommand(self, value):
      """
      Property target to set the rcp command.

      The value must be a non-empty string or C{None}.  Its value is stored in
      the two forms: "raw" as provided by the client, and "parsed" into a list
      suitable for being passed to L{util.executeCommand} via
      L{util.splitCommandLine}.  

      However, all the caller will ever see via the property is the actual
      value they set (which includes seeing C{None}, even if we translate that
      internally to C{DEF_RCP_COMMAND}).  Internally, we should always use
      C{self._rcpCommandList} if we want the actual command list.

      @raise ValueError: If the value is an empty string.
      """
      if value is None:
         self._rcpCommand = None
         self._rcpCommandList = DEF_RCP_COMMAND
      else:
         if len(value) >= 1:
            self._rcpCommand = value
            self._rcpCommandList = splitCommandLine(self._rcpCommand)
         else:
            raise ValueError("The rcp command must be a non-empty string.")

   def _getRcpCommand(self):
      """
      Property target used to get the rcp command.
      """
      return self._rcpCommand

   name = property(_getName, _setName, None, "Name of the peer (a valid DNS hostname).")
   collectDir = property(_getCollectDir, _setCollectDir, None, "Path to the peer's collect directory (an absolute local path).")
   workingDir = property(_getWorkingDir, _setWorkingDir, None, "Path to the peer's working directory (an absolute local path).")
   remoteUser = property(_getRemoteUser, _setRemoteUser, None, "Name of the Cedar Backup user on the remote peer.")
   localUser = property(_getLocalUser, _setLocalUser, None, "Name of the Cedar Backup user on the current host.")
   rcpCommand = property(_getRcpCommand, _setRcpCommand, None, "An rcp-compatible copy command to use for copying files.")


   #################
   # Public methods
   #################

   def stagePeer(self, targetDir, ownership=None, permissions=None):
      """
      Stages data from the peer into the indicated local target directory.

      The target directory must already exist before this method is called.  If
      passed in, ownership and permissions will be applied to the files that
      are copied.  

      @note: The returned count of copied files might be inaccurate if some of
      the copied files already existed in the staging directory prior to the
      copy taking place.  We don't clear the staging directory first, because
      some extension might also be using it.

      @note: If you have user/group as strings, call the L{util.getUidGid} function
      to get the associated uid/gid as an ownership tuple.

      @note: Unlike the local peer version of this method, an I/O error might
      or might not be raised if the directory is empty.  Since we're using a
      remote copy method, we just don't have the fine-grained control over our
      exceptions that's available when we can look directly at the filesystem,
      and we can't control whether the remote copy method thinks an empty
      directory is an error.  

      @param targetDir: Target directory to write data into
      @type targetDir: String representing a directory on disk

      @param ownership: Owner and group that the staged files should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the staged files should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @return: Number of files copied from the source directory to the target directory.

      @raise ValueError: If target directory is not a directory, does not exist or is not absolute.
      @raise ValueError: If a path cannot be encoded properly.
      @raise IOError: If there were no files to stage (i.e. the directory was empty)
      @raise IOError: If there is an IO error copying a file.
      @raise OSError: If there is an OS error copying or changing permissions on a file
      """
      targetDir = encodePath(targetDir)
      if not os.path.isabs(targetDir):
         logger.debug("Target directory [%s] not an absolute path." % targetDir)
         raise ValueError("Target directory must be an absolute path.")
      if not os.path.exists(targetDir) or not os.path.isdir(targetDir):
         logger.debug("Target directory [%s] is not a directory or does not exist on disk." % targetDir)
         raise ValueError("Target directory is not a directory or does not exist on disk.")
      count = RemotePeer._copyRemoteDir(self.remoteUser, self.localUser, self.name, 
                                        self._rcpCommand, self._rcpCommandList, 
                                        self.collectDir, targetDir, 
                                        ownership, permissions)
      if count == 0:
         raise IOError("Did not copy any files from local peer.")
      return count
      

   def checkCollectIndicator(self, collectIndicator=None):
      """
      Checks the collect indicator in the peer's staging directory.

      When a peer has completed collecting its backup files, it will write an
      empty indicator file into its collect directory.  This method checks to
      see whether that indicator has been written.  If the remote copy command
      fails, we return C{False} as if the file weren't there. 

      If you need to, you can override the name of the collect indicator file
      by passing in a different name.

      @note: Apparently, we can't count on all rcp-compatible implementations
      to return sensible errors for some error conditions.  As an example, the
      C{scp} command in Debian 'woody' returns a zero (normal) status even when
      it can't find a host or if the login or path is invalid.  Because of
      this, the implementation of this method is rather convoluted.

      @param collectIndicator: Name of the collect indicator file to check
      @type collectIndicator: String representing name of a file in the collect directory

      @return: Boolean true/false depending on whether the indicator exists.
      @raise ValueError: If a path cannot be encoded properly.
      """
      try:
         if collectIndicator is None:
            sourceFile = os.path.join(self.collectDir, DEF_COLLECT_INDICATOR)
            targetFile = os.path.join(self.workingDir, DEF_COLLECT_INDICATOR)
         else:
            collectIndicator = encodePath(collectIndicator)
            sourceFile = os.path.join(self.collectDir, collectIndicator)
            targetFile = os.path.join(self.workingDir, collectIndicator) 
         logger.debug("Fetch remote [%s] into [%s]." % (sourceFile, targetFile))
         if os.path.exists(targetFile):
            try:
               os.remove(targetFile)
            except:
               raise Exception("Internal error: target existed before it should.")
         try:
            RemotePeer._copyRemoteFile(self.remoteUser, self.localUser, self.name, 
                                       self._rcpCommand, self._rcpCommandList, 
                                       sourceFile, targetFile, 
                                       overwrite=False)
            if os.path.exists(targetFile):
               return True
            else:
               return False
         except:
            return False
      finally:
         if os.path.exists(targetFile):
            try:
               os.remove(targetFile)
            except: pass

   def writeStageIndicator(self, stageIndicator=None):
      """
      Writes the stage indicator in the peer's staging directory.

      When the master has completed collecting its backup files, it will write
      an empty indicator file into the peer's collect directory.  The presence
      of this file implies that the staging process is complete.

      If you need to, you can override the name of the stage indicator file by
      passing in a different name.

      @note: If you have user/group as strings, call the L{util.getUidGid} function
      to get the associated uid/gid as an ownership tuple.

      @note: This method's behavior is UNIX-specific.  It depends on the
      ability of L{tempfile.NamedTemporaryFile} to create files that can be
      opened more than once.

      @param stageIndicator: Name of the indicator file to write
      @type stageIndicator: String representing name of a file in the collect directory

      @raise ValueError: If a path cannot be encoded properly.
      @raise IOError: If there is an IO error creating the file.
      @raise OSError: If there is an OS error creating or changing permissions on the file
      """
      stageIndicator = encodePath(stageIndicator)
      sourceFile = tempfile.NamedTemporaryFile(dir=self.workingDir)
      if stageIndicator is None:
         sourceFile = os.path.join(self.workingDir, DEF_STAGE_INDICATOR)
         targetFile = os.path.join(self.collectDir, DEF_STAGE_INDICATOR)
      else:
         sourceFile = os.path.join(self.workingDir, DEF_STAGE_INDICATOR)
         targetFile = os.path.join(self.collectDir, stageIndicator)
      try:
         if not os.path.exists(sourceFile):
            open(sourceFile, "w").write("")
         RemotePeer._pushLocalFile(self.remoteUser, self.localUser, self.name, 
                                   self._rcpCommand, self._rcpCommandList, 
                                   sourceFile, targetFile)
      finally:
         if os.path.exists(sourceFile):
            try:
               os.remove(sourceFile)
            except: pass


   ##################
   # Private methods
   ##################

   def _getDirContents(path):
      """
      Returns the contents of a directory in terms of a Set.
      
      The directory's contents are read as a L{FilesystemList} containing only
      files, and then the list is converted into a L{sets.Set} object for later
      use.

      @param path: Directory path to get contents for
      @type path: String representing a path on disk

      @return: Set of files in the directory
      @raise ValueError: If path is not a directory or does not exist.
      """
      contents = FilesystemList()
      contents.excludeDirs = True
      contents.excludeLinks = True
      contents.addDirContents(path)
      return sets.Set(contents)
   _getDirContents = staticmethod(_getDirContents)

   def _copyRemoteDir(remoteUser, localUser, remoteHost, rcpCommand, rcpCommandList, 
                      sourceDir, targetDir, ownership=None, permissions=None):
      """
      Copies files from the source directory to the target directory.

      This function is not recursive.  Only the files in the directory will be
      copied.   Ownership and permissions will be left at their default values
      if new values are not specified.  Behavior when copying soft links from
      the collect directory is dependent on the behavior of the specified rcp
      command.

      @note: The returned count of copied files might be inaccurate if some of
      the copied files already existed in the staging directory prior to the
      copy taking place.  We don't clear the staging directory first, because
      some extension might also be using it.

      @note: If you have user/group as strings, call the L{util.getUidGid} function
      to get the associated uid/gid as an ownership tuple.

      @note: We don't have a good way of knowing exactly what files we copied
      down from the remote peer, unless we want to parse the output of the rcp
      command (ugh).  We could change permissions on everything in the target
      directory, but that's kind of ugly too.  Instead, we use Python's set
      functionality to figure out what files were added while we executed the
      rcp command.  This isn't perfect - for instance, it's not correct if
      someone else is messing with the directory at the same time we're doing
      the remote copy - but it's about as good as we're going to get.

      @note: Apparently, we can't count on all rcp-compatible implementations
      to return sensible errors for some error conditions.  As an example, the
      C{scp} command in Debian 'woody' returns a zero (normal) status even
      when it can't find a host or if the login or path is invalid.  We try
      to work around this by issuing C{IOError} if we don't copy any files from
      the remote host.

      @param remoteUser: Name of the Cedar Backup user on the remote peer
      @type remoteUser: String representing a username, valid via the copy command

      @param localUser: Name of the Cedar Backup user on the current host
      @type localUser: String representing a username, valid on the current host

      @param remoteHost: Hostname of the remote peer
      @type remoteHost: String representing a hostname, accessible via the copy command

      @param rcpCommand: An rcp-compatible copy command to use for copying files from the peer
      @type rcpCommand: String representing a system command including required arguments

      @param rcpCommandList: An rcp-compatible copy command to use for copying files
      @type rcpCommandList: Command as a list to be passed to L{util.executeCommand}

      @param sourceDir: Source directory
      @type sourceDir: String representing a directory on disk

      @param targetDir: Target directory
      @type targetDir: String representing a directory on disk

      @param ownership: Owner and group that the copied files should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the staged files should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @return: Number of files copied from the source directory to the target directory.

      @raise ValueError: If source or target is not a directory or does not exist.
      @raise IOError: If there is an IO error copying the files.
      """
      beforeSet = RemotePeer._getDirContents(targetDir)
      if localUser is not None:
         if os.getuid() != 0:
            raise IOError("Only root can remote copy as another user.")
         actualCommand = "%s %s@%s:%s/* %s" % (rcpCommand, remoteUser, remoteHost, sourceDir, targetDir)
         result = executeCommand(SU_COMMAND, [localUser, "-c", actualCommand])[0]
         if result != 0:
            raise IOError("Error (%d) copying files from remote host as local user [%s]." % (result, localUser))
      else:
         copySource = "%s@%s:%s/*" % (remoteUser, remoteHost, sourceDir)
         result = executeCommand(rcpCommandList, [copySource, targetDir])[0]
         if result != 0:
            raise IOError("Error (%d) copying files from remote host (no local user)." % result)
      afterSet = RemotePeer._getDirContents(targetDir)
      if len(afterSet) == 0:
         raise IOError("Did not copy any files from remote peer.")
      differenceSet = afterSet.difference(beforeSet)  # files we added as part of copy
      if len(differenceSet) == 0:
         raise IOError("Apparently did not copy any new files from remote peer.")
      for targetFile in differenceSet:
         if ownership is not None:
            os.chown(targetFile, ownership[0], ownership[1])
         if permissions is not None:
            os.chmod(targetFile, permissions)
      return len(differenceSet)
   _copyRemoteDir = staticmethod(_copyRemoteDir)

   def _copyRemoteFile(remoteUser, localUser, remoteHost, 
                       rcpCommand, rcpCommandList,
                       sourceFile, targetFile, ownership=None, 
                       permissions=None, overwrite=True):
      """
      Copies a remote source file to a target file.

      @note: Internally, we have to go through and escape any spaces in the
      source path with double-backslash, otherwise things get screwed up.   It
      doesn't seem to be required in the target path. I hope this is portable
      to various different rcp methods, but I guess it might not be (all I have
      to test with is OpenSSH).

      @note: If you have user/group as strings, call the L{util.getUidGid} function
      to get the associated uid/gid as an ownership tuple.

      @note: We will not overwrite a target file that exists when this method
      is invoked.  If the target already exists, we'll raise an exception.

      @note: Apparently, we can't count on all rcp-compatible implementations
      to return sensible errors for some error conditions.  As an example, the
      C{scp} command in Debian 'woody' returns a zero (normal) status even when
      it can't find a host or if the login or path is invalid.  We try to work
      around this by issuing C{IOError} the target file does not exist when
      we're done.

      @param remoteUser: Name of the Cedar Backup user on the remote peer
      @type remoteUser: String representing a username, valid via the copy command

      @param remoteHost: Hostname of the remote peer
      @type remoteHost: String representing a hostname, accessible via the copy command

      @param localUser: Name of the Cedar Backup user on the current host
      @type localUser: String representing a username, valid on the current host

      @param rcpCommand: An rcp-compatible copy command to use for copying files from the peer
      @type rcpCommand: String representing a system command including required arguments

      @param rcpCommandList: An rcp-compatible copy command to use for copying files
      @type rcpCommandList: Command as a list to be passed to L{util.executeCommand}

      @param sourceFile: Source file to copy
      @type sourceFile: String representing a file on disk, as an absolute path

      @param targetFile: Target file to create
      @type targetFile: String representing a file on disk, as an absolute path

      @param ownership: Owner and group that the copied should have
      @type ownership: Tuple of numeric ids C{(uid, gid)}

      @param permissions: Permissions that the staged files should have
      @type permissions: UNIX permissions mode, specified in octal (i.e. C{0640}).

      @param overwrite: Indicates whether it's OK to overwrite the target file.
      @type overwrite: Boolean true/false.

      @raise IOError: If the target file already exists.
      @raise IOError: If there is an IO error copying the file
      @raise OSError: If there is an OS error changing permissions on the file
      """
      if not overwrite:
         if os.path.exists(targetFile):
            raise IOError("Target file [%s] already exists." % targetFile)
      if localUser is not None:
         if os.getuid() != 0:
            raise IOError("Only root can remote copy as another user.")
         actualCommand = "%s %s@%s:%s %s" % (rcpCommand, remoteUser, remoteHost, sourceFile.replace(" ", "\\ "), targetFile)
         result = executeCommand(SU_COMMAND, [localUser, "-c", actualCommand])[0]
         if result != 0:
            raise IOError("Error (%d) copying [%s] from remote host as local user [%s]." % (result, sourceFile, localUser))
      else:
         copySource = "%s@%s:%s" % (remoteUser, remoteHost, sourceFile.replace(" ", "\\ "))
         result = executeCommand(rcpCommandList, [copySource, targetFile])[0]
         if result != 0:
            raise IOError("Error (%d) copying [%s] from remote host (no local user)." % (result, sourceFile))
      if not os.path.exists(targetFile):
         raise IOError("Apparently unable to copy file from remote host.")
      if ownership is not None:
         os.chown(targetFile, ownership[0], ownership[1])
      if permissions is not None:
         os.chmod(targetFile, permissions)
   _copyRemoteFile = staticmethod(_copyRemoteFile)

   def _pushLocalFile(remoteUser, localUser, remoteHost, 
                      rcpCommand, rcpCommandList,
                      sourceFile, targetFile, overwrite=True):
      """
      Copies a local source file to a remote host.

      @note: We will not overwrite a target file that exists when this method
      is invoked.  If the target already exists, we'll raise an exception.

      @note: Internally, we have to go through and escape any spaces in the
      source and target paths with double-backslash, otherwise things get
      screwed up.  I hope this is portable to various different rcp methods,
      but I guess it might not be (all I have to test with is OpenSSH).

      @note: If you have user/group as strings, call the L{util.getUidGid} function
      to get the associated uid/gid as an ownership tuple.

      @param remoteUser: Name of the Cedar Backup user on the remote peer
      @type remoteUser: String representing a username, valid via the copy command

      @param localUser: Name of the Cedar Backup user on the current host
      @type localUser: String representing a username, valid on the current host

      @param remoteHost: Hostname of the remote peer
      @type remoteHost: String representing a hostname, accessible via the copy command

      @param rcpCommand: An rcp-compatible copy command to use for copying files from the peer
      @type rcpCommand: String representing a system command including required arguments

      @param rcpCommandList: An rcp-compatible copy command to use for copying files
      @type rcpCommandList: Command as a list to be passed to L{util.executeCommand}

      @param sourceFile: Source file to copy
      @type sourceFile: String representing a file on disk, as an absolute path

      @param targetFile: Target file to create
      @type targetFile: String representing a file on disk, as an absolute path

      @param overwrite: Indicates whether it's OK to overwrite the target file.
      @type overwrite: Boolean true/false.

      @raise IOError: If there is an IO error copying the file
      @raise OSError: If there is an OS error changing permissions on the file
      """
      if not overwrite:
         if os.path.exists(targetFile):
            raise IOError("Target file [%s] already exists." % targetFile)
      if localUser is not None:
         if os.getuid() != 0:
            raise IOError("Only root can remote copy as another user.")
         actualCommand = '%s "%s" "%s@%s:%s"' % (rcpCommand, sourceFile, remoteUser, remoteHost, targetFile)
         result = executeCommand(SU_COMMAND, [localUser, "-c", actualCommand])[0]
         if result != 0:
            raise IOError("Error (%d) copying [%s] to remote host as local user [%s]." % (result, sourceFile, localUser))
      else:
         copyTarget = "%s@%s:%s" % (remoteUser, remoteHost, targetFile.replace(" ", "\\ "))
         result = executeCommand(rcpCommandList, [sourceFile.replace(" ", "\\ "), copyTarget])[0]
         if result != 0:
            raise IOError("Error (%d) copying [%s] to remote host (no local user)." % (result, sourceFile))
   _pushLocalFile = staticmethod(_pushLocalFile)

