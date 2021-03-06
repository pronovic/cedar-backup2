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
# Copyright (c) 2004-2008,2010 Kenneth J. Pronovici.
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
# Language : Python 2 (>= 2.7)
# Project  : Cedar Backup, release 2
# Purpose  : Provides filesystem-related objects.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

########################################################################
# Module documentation
########################################################################

"""
Provides filesystem-related objects.
@sort: FilesystemList, BackupFileList, PurgeItemList
@author: Kenneth J. Pronovici <pronovic@ieee.org>
"""


########################################################################
# Imported modules
########################################################################

# System modules
import os
import re
import math
import logging
import tarfile

# Cedar Backup modules
from CedarBackup2.knapsack import firstFit, bestFit, worstFit, alternateFit
from CedarBackup2.util import AbsolutePathList, UnorderedList, RegexList
from CedarBackup2.util import removeKeys, displayBytes, calculateFileAge, encodePath, dereferenceLink


########################################################################
# Module-wide variables
########################################################################

logger = logging.getLogger("CedarBackup2.log.filesystem")


########################################################################
# FilesystemList class definition
########################################################################

class FilesystemList(list):

   ######################
   # Class documentation
   ######################

   """
   Represents a list of filesystem items.

   This is a generic class that represents a list of filesystem items.  Callers
   can add individual files or directories to the list, or can recursively add
   the contents of a directory.  The class also allows for up-front exclusions
   in several forms (all files, all directories, all items matching a pattern,
   all items whose basename matches a pattern, or all directories containing a
   specific "ignore file").  Symbolic links are typically backed up
   non-recursively, i.e. the link to a directory is backed up, but not the
   contents of that link (we don't want to deal with recursive loops, etc.).

   The custom methods such as L{addFile} will only add items if they exist on
   the filesystem and do not match any exclusions that are already in place.
   However, since a FilesystemList is a subclass of Python's standard list
   class, callers can also add items to the list in the usual way, using
   methods like C{append()} or C{insert()}.  No validations apply to items
   added to the list in this way; however, many list-manipulation methods deal
   "gracefully" with items that don't exist in the filesystem, often by
   ignoring them.

   Once a list has been created, callers can remove individual items from the
   list using standard methods like C{pop()} or C{remove()} or they can use
   custom methods to remove specific types of entries or entries which match a
   particular pattern.

   @note: Regular expression patterns that apply to paths are assumed to be
   bounded at front and back by the beginning and end of the string, i.e. they
   are treated as if they begin with C{^} and end with C{$}.  This is true
   whether we are matching a complete path or a basename.

   @note: Some platforms, like Windows, do not support soft links.  On those
   platforms, the ignore-soft-links flag can be set, but it won't do any good
   because the operating system never reports a file as a soft link.

   @sort: __init__, addFile, addDir, addDirContents, removeFiles, removeDirs,
          removeLinks, removeMatch, removeInvalid, normalize,
          excludeFiles, excludeDirs, excludeLinks, excludePaths,
          excludePatterns, excludeBasenamePatterns, ignoreFile
   """


   ##############
   # Constructor
   ##############

   def __init__(self):
      """Initializes a list with no configured exclusions."""
      list.__init__(self)
      self._excludeFiles = False
      self._excludeDirs = False
      self._excludeLinks = False
      self._excludePaths = None
      self._excludePatterns = None
      self._excludeBasenamePatterns = None
      self._ignoreFile = None
      self.excludeFiles = False
      self.excludeLinks = False
      self.excludeDirs = False
      self.excludePaths = []
      self.excludePatterns = RegexList()
      self.excludeBasenamePatterns = RegexList()
      self.ignoreFile = None


   #############
   # Properties
   #############

   def _setExcludeFiles(self, value):
      """
      Property target used to set the exclude files flag.
      No validations, but we normalize the value to C{True} or C{False}.
      """
      if value:
         self._excludeFiles = True
      else:
         self._excludeFiles = False

   def _getExcludeFiles(self):
      """
      Property target used to get the exclude files flag.
      """
      return self._excludeFiles

   def _setExcludeDirs(self, value):
      """
      Property target used to set the exclude directories flag.
      No validations, but we normalize the value to C{True} or C{False}.
      """
      if value:
         self._excludeDirs = True
      else:
         self._excludeDirs = False

   def _getExcludeDirs(self):
      """
      Property target used to get the exclude directories flag.
      """
      return self._excludeDirs

   def _setExcludeLinks(self, value):
      """
      Property target used to set the exclude soft links flag.
      No validations, but we normalize the value to C{True} or C{False}.
      """
      if value:
         self._excludeLinks = True
      else:
         self._excludeLinks = False

   def _getExcludeLinks(self):
      """
      Property target used to get the exclude soft links flag.
      """
      return self._excludeLinks

   def _setExcludePaths(self, value):
      """
      Property target used to set the exclude paths list.
      A C{None} value is converted to an empty list.
      Elements do not have to exist on disk at the time of assignment.
      @raise ValueError: If any list element is not an absolute path.
      """
      self._excludePaths = AbsolutePathList()
      if value is not None:
         self._excludePaths.extend(value)

   def _getExcludePaths(self):
      """
      Property target used to get the absolute exclude paths list.
      """
      return self._excludePaths

   def _setExcludePatterns(self, value):
      """
      Property target used to set the exclude patterns list.
      A C{None} value is converted to an empty list.
      """
      self._excludePatterns = RegexList()
      if value is not None:
         self._excludePatterns.extend(value)

   def _getExcludePatterns(self):
      """
      Property target used to get the exclude patterns list.
      """
      return self._excludePatterns

   def _setExcludeBasenamePatterns(self, value):
      """
      Property target used to set the exclude basename patterns list.
      A C{None} value is converted to an empty list.
      """
      self._excludeBasenamePatterns = RegexList()
      if value is not None:
         self._excludeBasenamePatterns.extend(value)

   def _getExcludeBasenamePatterns(self):
      """
      Property target used to get the exclude basename patterns list.
      """
      return self._excludeBasenamePatterns

   def _setIgnoreFile(self, value):
      """
      Property target used to set the ignore file.
      The value must be a non-empty string if it is not C{None}.
      @raise ValueError: If the value is an empty string.
      """
      if value is not None:
         if len(value) < 1:
            raise ValueError("The ignore file must be a non-empty string.")
      self._ignoreFile = value

   def _getIgnoreFile(self):
      """
      Property target used to get the ignore file.
      """
      return self._ignoreFile

   excludeFiles = property(_getExcludeFiles, _setExcludeFiles, None, "Boolean indicating whether files should be excluded.")
   excludeDirs = property(_getExcludeDirs, _setExcludeDirs, None, "Boolean indicating whether directories should be excluded.")
   excludeLinks = property(_getExcludeLinks, _setExcludeLinks, None, "Boolean indicating whether soft links should be excluded.")
   excludePaths = property(_getExcludePaths, _setExcludePaths, None, "List of absolute paths to be excluded.")
   excludePatterns = property(_getExcludePatterns, _setExcludePatterns, None,
                              "List of regular expression patterns (matching complete path) to be excluded.")
   excludeBasenamePatterns = property(_getExcludeBasenamePatterns, _setExcludeBasenamePatterns,
                                      None, "List of regular expression patterns (matching basename) to be excluded.")
   ignoreFile = property(_getIgnoreFile, _setIgnoreFile, None, "Name of file which will cause directory contents to be ignored.")


   ##############
   # Add methods
   ##############

   def addFile(self, path):
      """
      Adds a file to the list.

      The path must exist and must be a file or a link to an existing file.  It
      will be added to the list subject to any exclusions that are in place.

      @param path: File path to be added to the list
      @type path: String representing a path on disk

      @return: Number of items added to the list.

      @raise ValueError: If path is not a file or does not exist.
      @raise ValueError: If the path could not be encoded properly.
      """
      path = encodePath(path)
      if not os.path.exists(path) or not os.path.isfile(path):
         logger.debug("Path [%s] is not a file or does not exist on disk.", path)
         raise ValueError("Path is not a file or does not exist on disk.")
      if self.excludeLinks and os.path.islink(path):
         logger.debug("Path [%s] is excluded based on excludeLinks.", path)
         return 0
      if self.excludeFiles:
         logger.debug("Path [%s] is excluded based on excludeFiles.", path)
         return 0
      if path in self.excludePaths:
         logger.debug("Path [%s] is excluded based on excludePaths.", path)
         return 0
      for pattern in self.excludePatterns:
         pattern = encodePath(pattern)  # use same encoding as filenames
         if re.compile(r"^%s$" % pattern).match(path): # safe to assume all are valid due to RegexList
            logger.debug("Path [%s] is excluded based on pattern [%s].", path, pattern)
            return 0
      for pattern in self.excludeBasenamePatterns: # safe to assume all are valid due to RegexList
         pattern = encodePath(pattern)  # use same encoding as filenames
         if re.compile(r"^%s$" % pattern).match(os.path.basename(path)):
            logger.debug("Path [%s] is excluded based on basename pattern [%s].", path, pattern)
            return 0
      self.append(path)
      logger.debug("Added file to list: [%s]", path)
      return 1

   def addDir(self, path):
      """
      Adds a directory to the list.

      The path must exist and must be a directory or a link to an existing
      directory.  It will be added to the list subject to any exclusions that
      are in place.  The L{ignoreFile} does not apply to this method, only to
      L{addDirContents}.

      @param path: Directory path to be added to the list
      @type path: String representing a path on disk

      @return: Number of items added to the list.

      @raise ValueError: If path is not a directory or does not exist.
      @raise ValueError: If the path could not be encoded properly.
      """
      path = encodePath(path)
      path = normalizeDir(path)
      if not os.path.exists(path) or not os.path.isdir(path):
         logger.debug("Path [%s] is not a directory or does not exist on disk.", path)
         raise ValueError("Path is not a directory or does not exist on disk.")
      if self.excludeLinks and os.path.islink(path):
         logger.debug("Path [%s] is excluded based on excludeLinks.", path)
         return 0
      if self.excludeDirs:
         logger.debug("Path [%s] is excluded based on excludeDirs.", path)
         return 0
      if path in self.excludePaths:
         logger.debug("Path [%s] is excluded based on excludePaths.", path)
         return 0
      for pattern in self.excludePatterns: # safe to assume all are valid due to RegexList
         pattern = encodePath(pattern)  # use same encoding as filenames
         if re.compile(r"^%s$" % pattern).match(path):
            logger.debug("Path [%s] is excluded based on pattern [%s].", path, pattern)
            return 0
      for pattern in self.excludeBasenamePatterns: # safe to assume all are valid due to RegexList
         pattern = encodePath(pattern)  # use same encoding as filenames
         if re.compile(r"^%s$" % pattern).match(os.path.basename(path)):
            logger.debug("Path [%s] is excluded based on basename pattern [%s].", path, pattern)
            return 0
      self.append(path)
      logger.debug("Added directory to list: [%s]", path)
      return 1

   def addDirContents(self, path, recursive=True, addSelf=True, linkDepth=0, dereference=False):
      """
      Adds the contents of a directory to the list.

      The path must exist and must be a directory or a link to a directory.
      The contents of the directory (as well as the directory path itself) will
      be recursively added to the list, subject to any exclusions that are in
      place.  If you only want the directory and its immediate contents to be
      added, then pass in C{recursive=False}.

      @note: If a directory's absolute path matches an exclude pattern or path,
      or if the directory contains the configured ignore file, then the
      directory and all of its contents will be recursively excluded from the
      list.

      @note: If the passed-in directory happens to be a soft link, it will be
      recursed.  However, the linkDepth parameter controls whether any soft
      links I{within} the directory will be recursed.  The link depth is
      maximum depth of the tree at which soft links should be followed.  So, a
      depth of 0 does not follow any soft links, a depth of 1 follows only
      links within the passed-in directory, a depth of 2 follows the links at
      the next level down, etc.

      @note: Any invalid soft links (i.e.  soft links that point to
      non-existent items) will be silently ignored.

      @note: The L{excludeDirs} flag only controls whether any given directory
      path itself is added to the list once it has been discovered.  It does
      I{not} modify any behavior related to directory recursion.

      @note: If you call this method I{on a link to a directory} that link will
      never be dereferenced (it may, however, be followed).

      @param path: Directory path whose contents should be added to the list
      @type path: String representing a path on disk

      @param recursive: Indicates whether directory contents should be added recursively.
      @type recursive: Boolean value

      @param addSelf: Indicates whether the directory itself should be added to the list.
      @type addSelf: Boolean value

      @param linkDepth: Maximum depth of the tree at which soft links should be followed
      @type linkDepth: Integer value, where zero means not to follow any soft links

      @param dereference: Indicates whether soft links, if followed, should be dereferenced
      @type dereference: Boolean value

      @return: Number of items recursively added to the list

      @raise ValueError: If path is not a directory or does not exist.
      @raise ValueError: If the path could not be encoded properly.
      """
      path = encodePath(path)
      path = normalizeDir(path)
      return self._addDirContentsInternal(path, addSelf, recursive, linkDepth, dereference)

   def _addDirContentsInternal(self, path, includePath=True, recursive=True, linkDepth=0, dereference=False):
      """
      Internal implementation of C{addDirContents}.

      This internal implementation exists due to some refactoring.  Basically,
      some subclasses have a need to add the contents of a directory, but not
      the directory itself.  This is different than the standard C{FilesystemList}
      behavior and actually ends up making a special case out of the first
      call in the recursive chain.  Since I don't want to expose the modified
      interface, C{addDirContents} ends up being wholly implemented in terms
      of this method.

      The linkDepth parameter controls whether soft links are followed when we
      are adding the contents recursively.  Any recursive calls reduce the
      value by one.  If the value zero or less, then soft links will just be
      added as directories, but will not be followed.  This means that links
      are followed to a I{constant depth} starting from the top-most directory.

      There is one difference between soft links and directories: soft links
      that are added recursively are not placed into the list explicitly.  This
      is because if we do add the links recursively, the resulting tar file
      gets a little confused (it has a link and a directory with the same
      name).

      @note: If you call this method I{on a link to a directory} that link will
      never be dereferenced (it may, however, be followed).

      @param path: Directory path whose contents should be added to the list.
      @param includePath: Indicates whether to include the path as well as contents.
      @param recursive: Indicates whether directory contents should be added recursively.
      @param linkDepth: Depth of soft links that should be followed
      @param dereference: Indicates whether soft links, if followed, should be dereferenced

      @return: Number of items recursively added to the list

      @raise ValueError: If path is not a directory or does not exist.
      """
      added = 0
      if not os.path.exists(path) or not os.path.isdir(path):
         logger.debug("Path [%s] is not a directory or does not exist on disk.", path)
         raise ValueError("Path is not a directory or does not exist on disk.")
      if path in self.excludePaths:
         logger.debug("Path [%s] is excluded based on excludePaths.", path)
         return added
      for pattern in self.excludePatterns: # safe to assume all are valid due to RegexList
         pattern = encodePath(pattern)  # use same encoding as filenames
         if re.compile(r"^%s$" % pattern).match(path):
            logger.debug("Path [%s] is excluded based on pattern [%s].", path, pattern)
            return added
      for pattern in self.excludeBasenamePatterns: # safe to assume all are valid due to RegexList
         pattern = encodePath(pattern)  # use same encoding as filenames
         if re.compile(r"^%s$" % pattern).match(os.path.basename(path)):
            logger.debug("Path [%s] is excluded based on basename pattern [%s].", path, pattern)
            return added
      if self.ignoreFile is not None and os.path.exists(os.path.join(path, self.ignoreFile)):
         logger.debug("Path [%s] is excluded based on ignore file.", path)
         return added
      if includePath:
         added += self.addDir(path)    # could actually be excluded by addDir, yet
      for entry in os.listdir(path):
         entrypath = os.path.join(path, entry)
         if os.path.isfile(entrypath):
            if linkDepth > 0 and dereference:
               derefpath = dereferenceLink(entrypath)
               if derefpath != entrypath:
                  added += self.addFile(derefpath)
            added += self.addFile(entrypath)
         elif os.path.isdir(entrypath):
            if os.path.islink(entrypath):
               if recursive:
                  if linkDepth > 0:
                     newDepth = linkDepth - 1
                     if dereference:
                        derefpath = dereferenceLink(entrypath)
                        if derefpath != entrypath:
                           added += self._addDirContentsInternal(derefpath, True, recursive, newDepth, dereference)
                        added += self.addDir(entrypath)
                     else:
                        added += self._addDirContentsInternal(entrypath, False, recursive, newDepth, dereference)
                  else:
                     added += self.addDir(entrypath)
               else:
                  added += self.addDir(entrypath)
            else:
               if recursive:
                  newDepth = linkDepth - 1
                  added += self._addDirContentsInternal(entrypath, True, recursive, newDepth, dereference)
               else:
                  added += self.addDir(entrypath)
      return added


   #################
   # Remove methods
   #################

   def removeFiles(self, pattern=None):
      """
      Removes file entries from the list.

      If C{pattern} is not passed in or is C{None}, then all file entries will
      be removed from the list.  Otherwise, only those file entries matching
      the pattern will be removed.  Any entry which does not exist on disk
      will be ignored (use L{removeInvalid} to purge those entries).

      This method might be fairly slow for large lists, since it must check the
      type of each item in the list.  If you know ahead of time that you want
      to exclude all files, then you will be better off setting L{excludeFiles}
      to C{True} before adding items to the list.

      @param pattern: Regular expression pattern representing entries to remove

      @return: Number of entries removed
      @raise ValueError: If the passed-in pattern is not a valid regular expression.
      """
      removed = 0
      if pattern is None:
         for entry in self[:]:
            if os.path.exists(entry) and os.path.isfile(entry):
               self.remove(entry)
               logger.debug("Removed path [%s] from list.", entry)
               removed += 1
      else:
         try:
            pattern = encodePath(pattern)  # use same encoding as filenames
            compiled = re.compile(pattern)
         except re.error:
            raise ValueError("Pattern is not a valid regular expression.")
         for entry in self[:]:
            if os.path.exists(entry) and os.path.isfile(entry):
               if compiled.match(entry):
                  self.remove(entry)
                  logger.debug("Removed path [%s] from list.", entry)
                  removed += 1
      logger.debug("Removed a total of %d entries.", removed)
      return removed

   def removeDirs(self, pattern=None):
      """
      Removes directory entries from the list.

      If C{pattern} is not passed in or is C{None}, then all directory entries
      will be removed from the list.  Otherwise, only those directory entries
      matching the pattern will be removed.  Any entry which does not exist on
      disk will be ignored (use L{removeInvalid} to purge those entries).

      This method might be fairly slow for large lists, since it must check the
      type of each item in the list.  If you know ahead of time that you want
      to exclude all directories, then you will be better off setting
      L{excludeDirs} to C{True} before adding items to the list (note that this
      will not prevent you from recursively adding the I{contents} of
      directories).

      @param pattern: Regular expression pattern representing entries to remove

      @return: Number of entries removed
      @raise ValueError: If the passed-in pattern is not a valid regular expression.
      """
      removed = 0
      if pattern is None:
         for entry in self[:]:
            if os.path.exists(entry) and os.path.isdir(entry):
               self.remove(entry)
               logger.debug("Removed path [%s] from list.", entry)
               removed += 1
      else:
         try:
            pattern = encodePath(pattern)  # use same encoding as filenames
            compiled = re.compile(pattern)
         except re.error:
            raise ValueError("Pattern is not a valid regular expression.")
         for entry in self[:]:
            if os.path.exists(entry) and os.path.isdir(entry):
               if compiled.match(entry):
                  self.remove(entry)
                  logger.debug("Removed path [%s] from list based on pattern [%s].", entry, pattern)
                  removed += 1
      logger.debug("Removed a total of %d entries.", removed)
      return removed

   def removeLinks(self, pattern=None):
      """
      Removes soft link entries from the list.

      If C{pattern} is not passed in or is C{None}, then all soft link entries
      will be removed from the list.  Otherwise, only those soft link entries
      matching the pattern will be removed.  Any entry which does not exist on
      disk will be ignored (use L{removeInvalid} to purge those entries).

      This method might be fairly slow for large lists, since it must check the
      type of each item in the list.  If you know ahead of time that you want
      to exclude all soft links, then you will be better off setting
      L{excludeLinks} to C{True} before adding items to the list.

      @param pattern: Regular expression pattern representing entries to remove

      @return: Number of entries removed
      @raise ValueError: If the passed-in pattern is not a valid regular expression.
      """
      removed = 0
      if pattern is None:
         for entry in self[:]:
            if os.path.exists(entry) and os.path.islink(entry):
               self.remove(entry)
               logger.debug("Removed path [%s] from list.", entry)
               removed += 1
      else:
         try:
            pattern = encodePath(pattern)  # use same encoding as filenames
            compiled = re.compile(pattern)
         except re.error:
            raise ValueError("Pattern is not a valid regular expression.")
         for entry in self[:]:
            if os.path.exists(entry) and os.path.islink(entry):
               if compiled.match(entry):
                  self.remove(entry)
                  logger.debug("Removed path [%s] from list based on pattern [%s].", entry, pattern)
                  removed += 1
      logger.debug("Removed a total of %d entries.", removed)
      return removed

   def removeMatch(self, pattern):
      """
      Removes from the list all entries matching a pattern.

      This method removes from the list all entries which match the passed in
      C{pattern}.  Since there is no need to check the type of each entry, it
      is faster to call this method than to call the L{removeFiles},
      L{removeDirs} or L{removeLinks} methods individually.  If you know which
      patterns you will want to remove ahead of time, you may be better off
      setting L{excludePatterns} or L{excludeBasenamePatterns} before adding
      items to the list.

      @note: Unlike when using the exclude lists, the pattern here is I{not}
      bounded at the front and the back of the string.  You can use any pattern
      you want.

      @param pattern: Regular expression pattern representing entries to remove

      @return: Number of entries removed.
      @raise ValueError: If the passed-in pattern is not a valid regular expression.
      """
      try:
         pattern = encodePath(pattern)  # use same encoding as filenames
         compiled = re.compile(pattern)
      except re.error:
         raise ValueError("Pattern is not a valid regular expression.")
      removed = 0
      for entry in self[:]:
         if compiled.match(entry):
            self.remove(entry)
            logger.debug("Removed path [%s] from list based on pattern [%s].", entry, pattern)
            removed += 1
      logger.debug("Removed a total of %d entries.", removed)
      return removed

   def removeInvalid(self):
      """
      Removes from the list all entries that do not exist on disk.

      This method removes from the list all entries which do not currently
      exist on disk in some form.  No attention is paid to whether the entries
      are files or directories.

      @return: Number of entries removed.
      """
      removed = 0
      for entry in self[:]:
         if not os.path.exists(entry):
            self.remove(entry)
            logger.debug("Removed path [%s] from list.", entry)
            removed += 1
      logger.debug("Removed a total of %d entries.", removed)
      return removed


   ##################
   # Utility methods
   ##################

   def normalize(self):
      """Normalizes the list, ensuring that each entry is unique."""
      orig = len(self)
      self.sort()
      dups = filter(lambda x, self=self: self[x] == self[x+1], range(0, len(self) - 1)) # pylint: disable=W0110
      items = map(lambda x, self=self: self[x], dups)                                   # pylint: disable=W0110
      map(self.remove, items)
      new = len(self)
      logger.debug("Completed normalizing list; removed %d items (%d originally, %d now).", new-orig, orig, new)

   def verify(self):
      """
      Verifies that all entries in the list exist on disk.
      @return: C{True} if all entries exist, C{False} otherwise.
      """
      for entry in self:
         if not os.path.exists(entry):
            logger.debug("Path [%s] is invalid; list is not valid.", entry)
            return False
      logger.debug("All entries in list are valid.")
      return True


########################################################################
# SpanItem class definition
########################################################################

class SpanItem(object): # pylint: disable=R0903
   """
   Item returned by L{BackupFileList.generateSpan}.
   """
   def __init__(self, fileList, size, capacity, utilization):
      """
      Create object.
      @param fileList: List of files
      @param size: Size (in bytes) of files
      @param utilization: Utilization, as a percentage (0-100)
      """
      self.fileList = fileList
      self.size = size
      self.capacity = capacity
      self.utilization = utilization


########################################################################
# BackupFileList class definition
########################################################################

class BackupFileList(FilesystemList): # pylint: disable=R0904

   ######################
   # Class documentation
   ######################

   """
   List of files to be backed up.

   A BackupFileList is a L{FilesystemList} containing a list of files to be
   backed up.  It only contains files, not directories (soft links are treated
   like files).  On top of the generic functionality provided by
   L{FilesystemList}, this class adds functionality to keep a hash (checksum)
   for each file in the list, and it also provides a method to calculate the
   total size of the files in the list and a way to export the list into tar
   form.

   @sort: __init__, addDir, totalSize, generateSizeMap, generateDigestMap,
          generateFitted, generateTarfile, removeUnchanged
   """

   ##############
   # Constructor
   ##############

   def __init__(self):
      """Initializes a list with no configured exclusions."""
      FilesystemList.__init__(self)


   ################################
   # Overridden superclass methods
   ################################

   def addDir(self, path):
      """
      Adds a directory to the list.

      Note that this class does not allow directories to be added by themselves
      (a backup list contains only files).  However, since links to directories
      are technically files, we allow them to be added.

      This method is implemented in terms of the superclass method, with one
      additional validation: the superclass method is only called if the
      passed-in path is both a directory and a link.  All of the superclass's
      existing validations and restrictions apply.

      @param path: Directory path to be added to the list
      @type path: String representing a path on disk

      @return: Number of items added to the list.

      @raise ValueError: If path is not a directory or does not exist.
      @raise ValueError: If the path could not be encoded properly.
      """
      path = encodePath(path)
      path = normalizeDir(path)
      if os.path.isdir(path) and not os.path.islink(path):
         return 0
      else:
         return FilesystemList.addDir(self, path)


   ##################
   # Utility methods
   ##################

   def totalSize(self):
      """
      Returns the total size among all files in the list.
      Only files are counted.
      Soft links that point at files are ignored.
      Entries which do not exist on disk are ignored.
      @return: Total size, in bytes
      """
      total = 0.0
      for entry in self:
         if os.path.isfile(entry) and not os.path.islink(entry):
            total += float(os.stat(entry).st_size)
      return total

   def generateSizeMap(self):
      """
      Generates a mapping from file to file size in bytes.
      The mapping does include soft links, which are listed with size zero.
      Entries which do not exist on disk are ignored.
      @return: Dictionary mapping file to file size
      """
      table = { }
      for entry in self:
         if os.path.islink(entry):
            table[entry] = 0.0
         elif os.path.isfile(entry):
            table[entry] = float(os.stat(entry).st_size)
      return table

   def generateDigestMap(self, stripPrefix=None):
      """
      Generates a mapping from file to file digest.

      Currently, the digest is an SHA hash, which should be pretty secure.  In
      the future, this might be a different kind of hash, but we guarantee that
      the type of the hash will not change unless the library major version
      number is bumped.

      Entries which do not exist on disk are ignored.

      Soft links are ignored.  We would end up generating a digest for the file
      that the soft link points at, which doesn't make any sense.

      If C{stripPrefix} is passed in, then that prefix will be stripped from
      each key when the map is generated.  This can be useful in generating two
      "relative" digest maps to be compared to one another.

      @param stripPrefix: Common prefix to be stripped from paths
      @type stripPrefix: String with any contents

      @return: Dictionary mapping file to digest value
      @see: L{removeUnchanged}
      """
      table = { }
      if stripPrefix is not None:
         for entry in self:
            if os.path.isfile(entry) and not os.path.islink(entry):
               table[entry.replace(stripPrefix, "", 1)] = BackupFileList._generateDigest(entry)
      else:
         for entry in self:
            if os.path.isfile(entry) and not os.path.islink(entry):
               table[entry] = BackupFileList._generateDigest(entry)
      return table

   @staticmethod
   def _generateDigest(path):
      """
      Generates an SHA digest for a given file on disk.

      The original code for this function used this simplistic implementation,
      which requires reading the entire file into memory at once in order to
      generate a digest value::

         sha.new(open(path).read()).hexdigest()

      Not surprisingly, this isn't an optimal solution.  The U{Simple file
      hashing <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/259109>}
      Python Cookbook recipe describes how to incrementally generate a hash
      value by reading in chunks of data rather than reading the file all at
      once.  The recipe relies on the the C{update()} method of the various
      Python hashing algorithms.

      In my tests using a 110 MB file on CD, the original implementation
      requires 111 seconds.  This implementation requires only 40-45 seconds,
      which is a pretty substantial speed-up.

      Experience shows that reading in around 4kB (4096 bytes) at a time yields
      the best performance.  Smaller reads are quite a bit slower, and larger
      reads don't make much of a difference.  The 4kB number makes me a little
      suspicious, and I think it might be related to the size of a filesystem
      read at the hardware level.  However, I've decided to just hardcode 4096
      until I have evidence that shows it's worthwhile making the read size
      configurable.

      @param path: Path to generate digest for.

      @return: ASCII-safe SHA digest for the file.
      @raise OSError: If the file cannot be opened.
      """
      # pylint: disable=C0103,E1101
      try:
         import hashlib
         s = hashlib.sha1()
      except ImportError:
         import sha
         s = sha.new()
      f = open(path, mode="rb")  # in case platform cares about binary reads
      readBytes = 4096  # see notes above
      while readBytes > 0:
         readString = f.read(readBytes)
         s.update(readString)
         readBytes = len(readString)
      f.close()
      digest = s.hexdigest()
      logger.debug("Generated digest [%s] for file [%s].", digest, path)
      return digest

   def generateFitted(self, capacity, algorithm="worst_fit"):
      """
      Generates a list of items that fit in the indicated capacity.

      Sometimes, callers would like to include every item in a list, but are
      unable to because not all of the items fit in the space available.  This
      method returns a copy of the list, containing only the items that fit in
      a given capacity.  A copy is returned so that we don't lose any
      information if for some reason the fitted list is unsatisfactory.

      The fitting is done using the functions in the knapsack module.  By
      default, the first fit algorithm is used, but you can also choose
      from best fit, worst fit and alternate fit.

      @param capacity: Maximum capacity among the files in the new list
      @type capacity: Integer, in bytes

      @param algorithm: Knapsack (fit) algorithm to use
      @type algorithm: One of "first_fit", "best_fit", "worst_fit", "alternate_fit"

      @return: Copy of list with total size no larger than indicated capacity
      @raise ValueError: If the algorithm is invalid.
      """
      table = self._getKnapsackTable()
      function = BackupFileList._getKnapsackFunction(algorithm)
      return function(table, capacity)[0]

   def generateSpan(self, capacity, algorithm="worst_fit"):
      """
      Splits the list of items into sub-lists that fit in a given capacity.

      Sometimes, callers need split to a backup file list into a set of smaller
      lists.  For instance, you could use this to "span" the files across a set
      of discs.

      The fitting is done using the functions in the knapsack module.  By
      default, the first fit algorithm is used, but you can also choose
      from best fit, worst fit and alternate fit.

      @note: If any of your items are larger than the capacity, then it won't
      be possible to find a solution.  In this case, a value error will be
      raised.

      @param capacity: Maximum capacity among the files in the new list
      @type capacity: Integer, in bytes

      @param algorithm: Knapsack (fit) algorithm to use
      @type algorithm: One of "first_fit", "best_fit", "worst_fit", "alternate_fit"

      @return: List of L{SpanItem} objects.

      @raise ValueError: If the algorithm is invalid.
      @raise ValueError: If it's not possible to fit some items
      """
      spanItems = []
      function = BackupFileList._getKnapsackFunction(algorithm)
      table = self._getKnapsackTable(capacity)
      iteration = 0
      while len(table) > 0:
         iteration += 1
         fit = function(table, capacity)
         if len(fit[0]) == 0:
            # Should never happen due to validations in _convertToKnapsackForm(), but let's be safe
            raise ValueError("After iteration %d, unable to add any new items." % iteration)
         removeKeys(table, fit[0])
         utilization = (float(fit[1])/float(capacity))*100.0
         item = SpanItem(fit[0], fit[1], capacity, utilization)
         spanItems.append(item)
      return spanItems

   def _getKnapsackTable(self, capacity=None):
      """
      Converts the list into the form needed by the knapsack algorithms.
      @return: Dictionary mapping file name to tuple of (file path, file size).
      """
      table = { }
      for entry in self:
         if os.path.islink(entry):
            table[entry] = (entry, 0.0)
         elif os.path.isfile(entry):
            size = float(os.stat(entry).st_size)
            if capacity is not None:
               if size > capacity:
                  raise ValueError("File [%s] cannot fit in capacity %s." % (entry, displayBytes(capacity)))
            table[entry] = (entry, size)
      return table

   @staticmethod
   def _getKnapsackFunction(algorithm):
      """
      Returns a reference to the function associated with an algorithm name.
      Algorithm name must be one of "first_fit", "best_fit", "worst_fit", "alternate_fit"
      @param algorithm: Name of the algorithm
      @return: Reference to knapsack function
      @raise ValueError: If the algorithm name is unknown.
      """
      if algorithm == "first_fit":
         return firstFit
      elif algorithm == "best_fit":
         return bestFit
      elif algorithm == "worst_fit":
         return worstFit
      elif algorithm == "alternate_fit":
         return alternateFit
      else:
         raise ValueError("Algorithm [%s] is invalid." % algorithm)

   def generateTarfile(self, path, mode='tar', ignore=False, flat=False):
      """
      Creates a tar file containing the files in the list.

      By default, this method will create uncompressed tar files.  If you pass
      in mode C{'targz'}, then it will create gzipped tar files, and if you
      pass in mode C{'tarbz2'}, then it will create bzipped tar files.

      The tar file will be created as a GNU tar archive, which enables extended
      file name lengths, etc.  Since GNU tar is so prevalent, I've decided that
      the extra functionality out-weighs the disadvantage of not being
      "standard".

      If you pass in C{flat=True}, then a "flat" archive will be created, and
      all of the files will be added to the root of the archive.  So, the file
      C{/tmp/something/whatever.txt} would be added as just C{whatever.txt}.

      By default, the whole method call fails if there are problems adding any
      of the files to the archive, resulting in an exception.  Under these
      circumstances, callers are advised that they might want to call
      L{removeInvalid()} and then attempt to extract the tar file a second
      time, since the most common cause of failures is a missing file (a file
      that existed when the list was built, but is gone again by the time the
      tar file is built).

      If you want to, you can pass in C{ignore=True}, and the method will
      ignore errors encountered when adding individual files to the archive
      (but not errors opening and closing the archive itself).

      We'll always attempt to remove the tarfile from disk if an exception will
      be thrown.

      @note: No validation is done as to whether the entries in the list are
      files, since only files or soft links should be in an object like this.
      However, to be safe, everything is explicitly added to the tar archive
      non-recursively so it's safe to include soft links to directories.

      @note: The Python C{tarfile} module, which is used internally here, is
      supposed to deal properly with long filenames and links.  In my testing,
      I have found that it appears to be able to add long really long filenames
      to archives, but doesn't do a good job reading them back out, even out of
      an archive it created.  Fortunately, all Cedar Backup does is add files
      to archives.

      @param path: Path of tar file to create on disk
      @type path: String representing a path on disk

      @param mode: Tar creation mode
      @type mode: One of either C{'tar'}, C{'targz'} or C{'tarbz2'}

      @param ignore: Indicates whether to ignore certain errors.
      @type ignore: Boolean

      @param flat: Creates "flat" archive by putting all items in root
      @type flat: Boolean

      @raise ValueError: If mode is not valid
      @raise ValueError: If list is empty
      @raise ValueError: If the path could not be encoded properly.
      @raise TarError: If there is a problem creating the tar file
      """
      # pylint: disable=E1101
      path = encodePath(path)
      if len(self) == 0: raise ValueError("Empty list cannot be used to generate tarfile.")
      if mode == 'tar': tarmode = "w:"
      elif mode == 'targz': tarmode = "w:gz"
      elif mode == 'tarbz2': tarmode = "w:bz2"
      else: raise ValueError("Mode [%s] is not valid." % mode)
      try:
         tar = tarfile.open(path, tarmode)
         try:
            tar.format = tarfile.GNU_FORMAT
         except AttributeError:
            tar.posix = False
         for entry in self:
            try:
               if flat:
                  tar.add(entry, arcname=os.path.basename(entry), recursive=False)
               else:
                  tar.add(entry, recursive=False)
            except tarfile.TarError, e:
               if not ignore:
                  raise e
               logger.info("Unable to add file [%s]; going on anyway.", entry)
            except OSError, e:
               if not ignore:
                  raise tarfile.TarError(e)
               logger.info("Unable to add file [%s]; going on anyway.", entry)
         tar.close()
      except tarfile.ReadError, e:
         try: tar.close()
         except: pass
         if os.path.exists(path):
            try: os.remove(path)
            except: pass
         raise tarfile.ReadError("Unable to open [%s]; maybe directory doesn't exist?" % path)
      except tarfile.TarError, e:
         try: tar.close()
         except: pass
         if os.path.exists(path):
            try: os.remove(path)
            except: pass
         raise e

   def removeUnchanged(self, digestMap, captureDigest=False):
      """
      Removes unchanged entries from the list.

      This method relies on a digest map as returned from L{generateDigestMap}.
      For each entry in C{digestMap}, if the entry also exists in the current
      list I{and} the entry in the current list has the same digest value as in
      the map, the entry in the current list will be removed.

      This method offers a convenient way for callers to filter unneeded
      entries from a list.  The idea is that a caller will capture a digest map
      from C{generateDigestMap} at some point in time (perhaps the beginning of
      the week), and will save off that map using C{pickle} or some other
      method.  Then, the caller could use this method sometime in the future to
      filter out any unchanged files based on the saved-off map.

      If C{captureDigest} is passed-in as C{True}, then digest information will
      be captured for the entire list before the removal step occurs using the
      same rules as in L{generateDigestMap}.  The check will involve a lookup
      into the complete digest map.

      If C{captureDigest} is passed in as C{False}, we will only generate a
      digest value for files we actually need to check, and we'll ignore any
      entry in the list which isn't a file that currently exists on disk.

      The return value varies depending on C{captureDigest}, as well.  To
      preserve backwards compatibility, if C{captureDigest} is C{False}, then
      we'll just return a single value representing the number of entries
      removed.  Otherwise, we'll return a tuple of C{(entries removed, digest
      map)}.  The returned digest map will be in exactly the form returned by
      L{generateDigestMap}.

      @note: For performance reasons, this method actually ends up rebuilding
      the list from scratch.  First, we build a temporary dictionary containing
      all of the items from the original list.  Then, we remove items as needed
      from the dictionary (which is faster than the equivalent operation on a
      list).  Finally, we replace the contents of the current list based on the
      keys left in the dictionary.  This should be transparent to the caller.

      @param digestMap: Dictionary mapping file name to digest value.
      @type digestMap: Map as returned from L{generateDigestMap}.

      @param captureDigest: Indicates that digest information should be captured.
      @type captureDigest: Boolean

      @return: Results as discussed above (format varies based on arguments)
      """
      if captureDigest:
         removed = 0
         table = {}
         captured = {}
         for entry in self:
            if os.path.isfile(entry) and not os.path.islink(entry):
               table[entry] = BackupFileList._generateDigest(entry)
               captured[entry] = table[entry]
            else:
               table[entry] = None
         for entry in digestMap.keys():
            if table.has_key(entry):
               if table[entry] is not None:  # equivalent to file/link check in other case
                  digest = table[entry]
                  if digest == digestMap[entry]:
                     removed += 1
                     del table[entry]
                     logger.debug("Discarded unchanged file [%s].", entry)
         self[:] = table.keys()
         return (removed, captured)
      else:
         removed = 0
         table = {}
         for entry in self:
            table[entry] = None
         for entry in digestMap.keys():
            if table.has_key(entry):
               if os.path.isfile(entry) and not os.path.islink(entry):
                  digest = BackupFileList._generateDigest(entry)
                  if digest == digestMap[entry]:
                     removed += 1
                     del table[entry]
                     logger.debug("Discarded unchanged file [%s].", entry)
         self[:] = table.keys()
         return removed


########################################################################
# PurgeItemList class definition
########################################################################

class PurgeItemList(FilesystemList): # pylint: disable=R0904

   ######################
   # Class documentation
   ######################

   """
   List of files and directories to be purged.

   A PurgeItemList is a L{FilesystemList} containing a list of files and
   directories to be purged.  On top of the generic functionality provided by
   L{FilesystemList}, this class adds functionality to remove items that are
   too young to be purged, and to actually remove each item in the list from
   the filesystem.

   The other main difference is that when you add a directory's contents to a
   purge item list, the directory itself is not added to the list.  This way,
   if someone asks to purge within in C{/opt/backup/collect}, that directory
   doesn't get removed once all of the files within it is gone.
   """

   ##############
   # Constructor
   ##############

   def __init__(self):
      """Initializes a list with no configured exclusions."""
      FilesystemList.__init__(self)


   ##############
   # Add methods
   ##############

   def addDirContents(self, path, recursive=True, addSelf=True, linkDepth=0, dereference=False):
      """
      Adds the contents of a directory to the list.

      The path must exist and must be a directory or a link to a directory.
      The contents of the directory (but I{not} the directory path itself) will
      be recursively added to the list, subject to any exclusions that are in
      place.  If you only want the directory and its contents to be added, then
      pass in C{recursive=False}.

      @note: If a directory's absolute path matches an exclude pattern or path,
      or if the directory contains the configured ignore file, then the
      directory and all of its contents will be recursively excluded from the
      list.

      @note: If the passed-in directory happens to be a soft link, it will be
      recursed.  However, the linkDepth parameter controls whether any soft
      links I{within} the directory will be recursed.  The link depth is
      maximum depth of the tree at which soft links should be followed.  So, a
      depth of 0 does not follow any soft links, a depth of 1 follows only
      links within the passed-in directory, a depth of 2 follows the links at
      the next level down, etc.

      @note: Any invalid soft links (i.e.  soft links that point to
      non-existent items) will be silently ignored.

      @note: The L{excludeDirs} flag only controls whether any given soft link
      path itself is added to the list once it has been discovered.  It does
      I{not} modify any behavior related to directory recursion.

      @note: The L{excludeDirs} flag only controls whether any given directory
      path itself is added to the list once it has been discovered.  It does
      I{not} modify any behavior related to directory recursion.

      @note: If you call this method I{on a link to a directory} that link will
      never be dereferenced (it may, however, be followed).

      @param path: Directory path whose contents should be added to the list
      @type path: String representing a path on disk

      @param recursive: Indicates whether directory contents should be added recursively.
      @type recursive: Boolean value

      @param addSelf: Ignored in this subclass.

      @param linkDepth: Depth of soft links that should be followed
      @type linkDepth: Integer value, where zero means not to follow any soft links

      @param dereference: Indicates whether soft links, if followed, should be dereferenced
      @type dereference: Boolean value

      @return: Number of items recursively added to the list

      @raise ValueError: If path is not a directory or does not exist.
      @raise ValueError: If the path could not be encoded properly.
      """
      path = encodePath(path)
      path = normalizeDir(path)
      return super(PurgeItemList, self)._addDirContentsInternal(path, False, recursive, linkDepth, dereference)


   ##################
   # Utility methods
   ##################

   def removeYoungFiles(self, daysOld):
      """
      Removes from the list files younger than a certain age (in days).

      Any file whose "age" in days is less than (C{<}) the value of the
      C{daysOld} parameter will be removed from the list so that it will not be
      purged later when L{purgeItems} is called.  Directories and soft links
      will be ignored.

      The "age" of a file is the amount of time since the file was last used,
      per the most recent of the file's C{st_atime} and C{st_mtime} values.

      @note: Some people find the "sense" of this method confusing or
      "backwards".  Keep in mind that this method is used to remove items
      I{from the list}, not from the filesystem!  It removes from the list
      those items that you would I{not} want to purge because they are too
      young.  As an example, passing in C{daysOld} of zero (0) would remove
      from the list no files, which would result in purging all of the files
      later.  I would be happy to make a synonym of this method with an
      easier-to-understand "sense", if someone can suggest one.

      @param daysOld: Minimum age of files that are to be kept in the list.
      @type daysOld: Integer value >= 0.

      @return: Number of entries removed
      """
      removed = 0
      daysOld = int(daysOld)
      if daysOld < 0:
         raise ValueError("Days old value must be an integer >= 0.")
      for entry in self[:]:
         if os.path.isfile(entry) and not os.path.islink(entry):
            try:
               ageInDays = calculateFileAge(entry)
               ageInWholeDays = math.floor(ageInDays)
               if ageInWholeDays < 0: ageInWholeDays = 0
               if ageInWholeDays < daysOld:
                  removed += 1
                  self.remove(entry)
            except OSError:
               pass
      return removed

   def purgeItems(self):
      """
      Purges all items in the list.

      Every item in the list will be purged.  Directories in the list will
      I{not} be purged recursively, and hence will only be removed if they are
      empty.  Errors will be ignored.

      To faciliate easy removal of directories that will end up being empty,
      the delete process happens in two passes: files first (including soft
      links), then directories.

      @return: Tuple containing count of (files, dirs) removed
      """
      files = 0
      dirs = 0
      for entry in self:
         if os.path.exists(entry) and (os.path.isfile(entry) or os.path.islink(entry)):
            try:
               os.remove(entry)
               files += 1
               logger.debug("Purged file [%s].", entry)
            except OSError:
               pass
      for entry in self:
         if os.path.exists(entry) and os.path.isdir(entry) and not os.path.islink(entry):
            try:
               os.rmdir(entry)
               dirs += 1
               logger.debug("Purged empty directory [%s].", entry)
            except OSError:
               pass
      return (files, dirs)


########################################################################
# Public functions
########################################################################

##########################
# normalizeDir() function
##########################

def normalizeDir(path):
   """
   Normalizes a directory name.

   For our purposes, a directory name is normalized by removing the trailing
   path separator, if any.  This is important because we want directories to
   appear within lists in a consistent way, although from the user's
   perspective passing in C{/path/to/dir/} and C{/path/to/dir} are equivalent.

   @param path: Path to be normalized.
   @type path: String representing a path on disk

   @return: Normalized path, which should be equivalent to the original.
   """
   if path != os.sep and path[-1:] == os.sep:
      return path[:-1]
   return path


#############################
# compareContents() function
#############################

def compareContents(path1, path2, verbose=False):
   """
   Compares the contents of two directories to see if they are equivalent.

   The two directories are recursively compared.  First, we check whether they
   contain exactly the same set of files.  Then, we check to see every given
   file has exactly the same contents in both directories.

   This is all relatively simple to implement through the magic of
   L{BackupFileList.generateDigestMap}, which knows how to strip a path prefix
   off the front of each entry in the mapping it generates.  This makes our
   comparison as simple as creating a list for each path, then generating a
   digest map for each path and comparing the two.

   If no exception is thrown, the two directories are considered identical.

   If the C{verbose} flag is C{True}, then an alternate (but slower) method is
   used so that any thrown exception can indicate exactly which file caused the
   comparison to fail.  The thrown C{ValueError} exception distinguishes
   between the directories containing different files, and containing the same
   files with differing content.

   @note: Symlinks are I{not} followed for the purposes of this comparison.

   @param path1: First path to compare.
   @type path1: String representing a path on disk

   @param path2: First path to compare.
   @type path2: String representing a path on disk

   @param verbose: Indicates whether a verbose response should be given.
   @type verbose: Boolean

   @raise ValueError: If a directory doesn't exist or can't be read.
   @raise ValueError: If the two directories are not equivalent.
   @raise IOError: If there is an unusual problem reading the directories.
   """
   try:
      path1List = BackupFileList()
      path1List.addDirContents(path1)
      path1Digest = path1List.generateDigestMap(stripPrefix=normalizeDir(path1))
      path2List = BackupFileList()
      path2List.addDirContents(path2)
      path2Digest = path2List.generateDigestMap(stripPrefix=normalizeDir(path2))
      compareDigestMaps(path1Digest, path2Digest, verbose)
   except IOError, e:
      logger.error("I/O error encountered during consistency check.")
      raise e

def compareDigestMaps(digest1, digest2, verbose=False):
   """
   Compares two digest maps and throws an exception if they differ.

   @param digest1: First digest to compare.
   @type digest1: Digest as returned from BackupFileList.generateDigestMap()

   @param digest2: Second digest to compare.
   @type digest2: Digest as returned from BackupFileList.generateDigestMap()

   @param verbose: Indicates whether a verbose response should be given.
   @type verbose: Boolean

   @raise ValueError: If the two directories are not equivalent.
   """
   if not verbose:
      if digest1 != digest2:
         raise ValueError("Consistency check failed.")
   else:
      list1 = UnorderedList(digest1.keys())
      list2 = UnorderedList(digest2.keys())
      if list1 != list2:
         raise ValueError("Directories contain a different set of files.")
      for key in list1:
         if digest1[key] != digest2[key]:
            raise ValueError("File contents for [%s] vary between directories." % key)

