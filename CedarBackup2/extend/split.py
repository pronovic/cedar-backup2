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
# Project  : Official Cedar Backup Extensions
# Revision : $Id$
# Purpose  : Provides an extension to split up large files in staging directories.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

########################################################################
# Module documentation
########################################################################

"""
Provides an extension to split up large files in staging directories.

When this extension is executed, it will look through the configured Cedar
Backup staging directory for files exceeding a specified size limit, and split
them down into smaller files using the 'split' utility.  Any directory which
has already been split (as indicated by the C{cback.split} file) will be
ignored.

This extension requires a new configuration section <split> and is intended
to be run immediately after the standard stage action or immediately before the
standard store action.  Aside from its own configuration, it requires the
options and staging configuration sections in the standard Cedar Backup
configuration file.

@author: Kenneth J. Pronovici <pronovic@ieee.org>
"""

########################################################################
# Imported modules
########################################################################

# System modules
import os
import re
import logging

# Cedar Backup modules
from CedarBackup2.filesystem import FilesystemList
from CedarBackup2.util import resolveCommand, executeCommand, convertSize
from CedarBackup2.util import changeOwnership, buildNormalizedPath
from CedarBackup2.util import UNIT_BYTES, UNIT_KBYTES, UNIT_MBYTES, UNIT_GBYTES
from CedarBackup2.xmlutil import createInputDom, addContainerNode, addStringNode
from CedarBackup2.xmlutil import readFirstChild, readString
from CedarBackup2.actions.util import findDailyDirs, writeIndicatorFile, getBackupFiles


########################################################################
# Module-wide constants and variables
########################################################################

logger = logging.getLogger("CedarBackup2.log.extend.split")

SPLIT_COMMAND = [ "split", ]
SPLIT_INDICATOR = "cback.split"

VALID_BYTE_UNITS = [ UNIT_BYTES, UNIT_KBYTES, UNIT_MBYTES, UNIT_GBYTES, ]


########################################################################
# ByteQuantity class definition
########################################################################

class ByteQuantity(object):

   """
   Class representing a byte quantity.

   A byte quantity has both a quantity and a byte-related unit.  Units are
   maintained using the constants from util.py.

   The quantity is maintained internally as a string so that issues of
   precision can be avoided.  It really isn't possible to store a floating
   point number here while being able to losslessly translate back and forth
   between XML and object representations.  (Perhaps the Python 2.4 Decimal
   class would have been an option, but I want to stay compatible with Python
   2.3.)

   Even though the quantity is maintained as a string, the string must be in a
   valid floating point positive number.  Technically, any floating point
   string format supported by Python is allowble.  However, it does not make
   sense to have a negative quantity of bytes in this context.  

   @sort: __init__, __repr__, __str__, __cmp__, quantity, units
   """

   def __init__(self, quantity=None, units=None):
      """
      Constructor for the C{ByteQuantity} class.

      @param quantity: Quantity of bytes, as string ("1.25")
      @param units: Unit of bytes, one of VALID_BYTE_UNITS

      @raise ValueError: If one of the values is invalid.
      """
      self._quantity = None
      self._units = None
      self.quantity = quantity
      self.units = units

   def __repr__(self):
      """
      Official string representation for class instance.
      """
      return "ByteQuantity(%s, %s)" % (self.quantity, self.units)

   def __str__(self):
      """
      Informal string representation for class instance.
      """
      return self.__repr__()

   def __cmp__(self, other):
      """
      Definition of equals operator for this class.
      Lists within this class are "unordered" for equality comparisons.
      @param other: Other object to compare to.
      @return: -1/0/1 depending on whether self is C{<}, C{=} or C{>} other.
      """
      if other is None:
         return 1
      if self._quantity != other._quantity:
         if self._quantity < other._quantity:
            return -1
         else:
            return 1
      if self._units != other._units:
         if self._units < other._units:
            return -1
         else:
            return 1
      return 0

   def _setQuantity(self, value):
      """
      Property target used to set the quantity
      The value must be a non-empty string if it is not C{None}.
      @raise ValueError: If the value is an empty string.
      @raise ValueError: If the value is not a valid floating point number
      @raise ValueError: If the value is less than zero
      """
      if value is not None:
         if len(value) < 1:
            raise ValueError("Quantity must be a non-empty string.")
         floatValue = float(value)
         if floatValue < 0.0:
            raise ValueError("Quantity cannot be negative.")
      self._quantity = value # keep around string

   def _getQuantity(self):
      """
      Property target used to get the quantity.
      """
      return self._quantity

   def _setUnits(self, value):
      """
      Property target used to set the units value.
      If not C{None}, the units value must be one of the values in L{VALID_BYTE_UNITS}.
      @raise ValueError: If the value is not valid.
      """
      if value is not None:
         if value not in VALID_BYTE_UNITS:
            raise ValueError("Units value must be one of %s." % VALID_BYTE_UNITS)
      self._units = value

   def _getUnits(self):
      """
      Property target used to get the units value.
      """
      return self._units

   quantity = property(_getQuantity, _setQuantity, None, doc="Byte quantity, as a string")
   units = property(_getUnits, _setUnits, None, doc="Units for byte quantity, for instance UNIT_BYTES")


########################################################################
# SplitConfig class definition
########################################################################

class SplitConfig(object):

   """
   Class representing split configuration.

   Split configuration is used for splitting staging directories.

   The following restrictions exist on data in this class:

      - The size limit must be a ByteQuantity
      - The split size must be a ByteQuantity

   @sort: __init__, __repr__, __str__, __cmp__, sizeLimit, splitSize
   """

   def __init__(self, sizeLimit=None, splitSize=None):
      """
      Constructor for the C{SplitCOnfig} class.

      @param sizeLimit: Size limit of the files, in bytes
      @param splitSize: Size that files exceeding the limit will be split into, in bytes

      @raise ValueError: If one of the values is invalid.
      """
      self._sizeLimit = None
      self._splitSize = None
      self.sizeLimit = sizeLimit
      self.splitSize = splitSize

   def __repr__(self):
      """
      Official string representation for class instance.
      """
      return "SplitConfig(%s, %s)" % (self.sizeLimit, self.splitSize)

   def __str__(self):
      """
      Informal string representation for class instance.
      """
      return self.__repr__()

   def __cmp__(self, other):
      """
      Definition of equals operator for this class.
      Lists within this class are "unordered" for equality comparisons.
      @param other: Other object to compare to.
      @return: -1/0/1 depending on whether self is C{<}, C{=} or C{>} other.
      """
      if other is None:
         return 1
      if self._sizeLimit != other._sizeLimit:
         if self._sizeLimit < other._sizeLimit:
            return -1
         else:
            return 1
      if self._splitSize != other._splitSize:
         if self._splitSize < other._splitSize:
            return -1
         else:
            return 1
      return 0

   def _setSizeLimit(self, value):
      """
      Property target used to set the size limit.
      If not C{None}, the value must be a C{ByteQuantity} object.
      @raise ValueError: If the value is not a C{ByteQuantity}
      """
      if value is None:
         self._sizeLimit = None
      else:
         if not isinstance(value, ByteQuantity):
            raise ValueError("Value must be a C{ByteQuantity} object.")
         self._sizeLimit = value

   def _getSizeLimit(self):
      """
      Property target used to get the size limit.
      """
      return self._sizeLimit

   def _setSplitSize(self, value):
      """
      Property target used to set the split size.
      If not C{None}, the value must be a C{ByteQuantity} object.
      @raise ValueError: If the value is not a C{ByteQuantity}
      """
      if value is None:
         self._splitSize = None
      else:
         if not isinstance(value, ByteQuantity):
            raise ValueError("Value must be a C{ByteQuantity} object.")
         self._splitSize = value

   def _getSplitSize(self):
      """
      Property target used to get the split size.
      """
      return self._splitSize

   sizeLimit = property(_getSizeLimit, _setSizeLimit, None, doc="Size limit, as a ByteQuantity")
   splitSize = property(_getSplitSize, _setSplitSize, None, doc="Split size, as a ByteQuantity")


########################################################################
# LocalConfig class definition
########################################################################

class LocalConfig(object):

   """
   Class representing this extension's configuration document.

   This is not a general-purpose configuration object like the main Cedar
   Backup configuration object.  Instead, it just knows how to parse and emit
   split-specific configuration values.  Third parties who need to read and
   write configuration related to this extension should access it through the
   constructor, C{validate} and C{addConfig} methods.

   @note: Lists within this class are "unordered" for equality comparisons.

   @sort: __init__, __repr__, __str__, __cmp__, split, validate, addConfig
   """

   def __init__(self, xmlData=None, xmlPath=None, validate=True):
      """
      Initializes a configuration object.

      If you initialize the object without passing either C{xmlData} or
      C{xmlPath} then configuration will be empty and will be invalid until it
      is filled in properly.

      No reference to the original XML data or original path is saved off by
      this class.  Once the data has been parsed (successfully or not) this
      original information is discarded.

      Unless the C{validate} argument is C{False}, the L{LocalConfig.validate}
      method will be called (with its default arguments) against configuration
      after successfully parsing any passed-in XML.  Keep in mind that even if
      C{validate} is C{False}, it might not be possible to parse the passed-in
      XML document if lower-level validations fail.

      @note: It is strongly suggested that the C{validate} option always be set
      to C{True} (the default) unless there is a specific need to read in
      invalid configuration from disk.  

      @param xmlData: XML data representing configuration.
      @type xmlData: String data.

      @param xmlPath: Path to an XML file on disk.
      @type xmlPath: Absolute path to a file on disk.

      @param validate: Validate the document after parsing it.
      @type validate: Boolean true/false.

      @raise ValueError: If both C{xmlData} and C{xmlPath} are passed-in.
      @raise ValueError: If the XML data in C{xmlData} or C{xmlPath} cannot be parsed.
      @raise ValueError: If the parsed configuration document is not valid.
      """
      self._split = None
      self.split = None
      if xmlData is not None and xmlPath is not None:
         raise ValueError("Use either xmlData or xmlPath, but not both.")
      if xmlData is not None:
         self._parseXmlData(xmlData)
         if validate:
            self.validate()
      elif xmlPath is not None:
         xmlData = open(xmlPath).read()
         self._parseXmlData(xmlData)
         if validate:
            self.validate()

   def __repr__(self):
      """
      Official string representation for class instance.
      """
      return "LocalConfig(%s)" % (self.split)

   def __str__(self):
      """
      Informal string representation for class instance.
      """
      return self.__repr__()

   def __cmp__(self, other):
      """
      Definition of equals operator for this class.
      Lists within this class are "unordered" for equality comparisons.
      @param other: Other object to compare to.
      @return: -1/0/1 depending on whether self is C{<}, C{=} or C{>} other.
      """
      if other is None:
         return 1
      if self._split != other._split:
         if self._split < other._split:
            return -1
         else:
            return 1
      return 0

   def _setSplit(self, value):
      """
      Property target used to set the split configuration value.
      If not C{None}, the value must be a C{SplitConfig} object.
      @raise ValueError: If the value is not a C{SplitConfig}
      """
      if value is None:
         self._split = None
      else:
         if not isinstance(value, SplitConfig):
            raise ValueError("Value must be a C{SplitConfig} object.")
         self._split = value

   def _getSplit(self):
      """
      Property target used to get the split configuration value.
      """
      return self._split

   split = property(_getSplit, _setSplit, None, "Split configuration in terms of a C{SplitConfig} object.")

   def validate(self):
      """
      Validates configuration represented by the object.

      Split configuration must be filled in.  Within that, both the size limit
      and split size must be filled in.

      @raise ValueError: If one of the validations fails.
      """
      if self.split is None:
         raise ValueError("Split section is required.")
      if self.split.sizeLimit is None:
         raise ValueError("Size limit must be set.")
      if self.split.splitSize is None:
         raise ValueError("Split size must be set.")

   def addConfig(self, xmlDom, parentNode):
      """
      Adds a <split> configuration section as the next child of a parent.

      Third parties should use this function to write configuration related to
      this extension.

      We add the following fields to the document::

         sizeLimit      //cb_config/split/size_limit
         splitSize      //cb_config/split/split_size

      @param xmlDom: DOM tree as from C{impl.createDocument()}.
      @param parentNode: Parent that the section should be appended to.
      """
      if self.split is not None:
         sectionNode = addContainerNode(xmlDom, parentNode, "split")
         LocalConfig._addByteQuantityNode(xmlDom, sectionNode, "size_limit", self.split.sizeLimit)
         LocalConfig._addByteQuantityNode(xmlDom, sectionNode, "split_size", self.split.splitSize)

   def _parseXmlData(self, xmlData):
      """
      Internal method to parse an XML string into the object.

      This method parses the XML document into a DOM tree (C{xmlDom}) and then
      calls a static method to parse the split configuration section.

      @param xmlData: XML data to be parsed
      @type xmlData: String data

      @raise ValueError: If the XML cannot be successfully parsed.
      """
      (xmlDom, parentNode) = createInputDom(xmlData)
      self._split = LocalConfig._parseSplit(parentNode)

   def _parseSplit(parent):
      """
      Parses an split configuration section.
      
      We read the following individual fields::

         sizeLimit      //cb_config/split/size_limit
         splitSize      //cb_config/split/split_size

      @param parent: Parent node to search beneath.

      @return: C{EncryptConfig} object or C{None} if the section does not exist.
      @raise ValueError: If some filled-in value is invalid.
      """
      split = None
      section = readFirstChild(parent, "split")
      if section is not None:
         split = SplitConfig()
         split.sizeLimit = LocalConfig._readByteQuantity(section, "size_limit")
         split.splitSize = LocalConfig._readByteQuantity(section, "split_size")
      return split
   _parseSplit = staticmethod(_parseSplit)

   def _readByteQuantity(parent, name):
      """
      Read a byte size value from an XML document.

      A byte size value is an interpreted string value.  If the string value
      ends with "MB" or "GB", then the string before that is interpreted as
      megabytes or gigabytes.  Otherwise, it is intepreted as bytes.  

      @param parent: Parent node to search beneath.
      @param name: Name of node to search for.

      @return: ByteQuantity parsed from XML document
      """
      data = readString(parent, name)
      if data is None:
         return None
      data = data.strip()
      if data.endswith("KB"):
         quantity = data[0:data.rfind("KB")].strip()
         units = UNIT_KBYTES
      elif data.endswith("MB"):
         quantity = data[0:data.rfind("MB")].strip()
         units = UNIT_MBYTES;
      elif data.endswith("GB"):
         quantity = data[0:data.rfind("GB")].strip()
         units = UNIT_GBYTES
      else:
         quantity = data.strip()
         units = UNIT_BYTES
      return ByteQuantity(quantity, units)
   _readByteQuantity = staticmethod(_readByteQuantity)

   def _addByteQuantityNode(xmlDom, parentNode, nodeName, byteQuantity):
      """
      Adds a text node as the next child of a parent, to contain a byte size.

      If the C{byteQuantity} is None, then the node will be created, but will
      be empty (i.e. will contain no text node child).

      The size in bytes will be normalized.  If it is larger than 1.0 GB, it will
      be shown in GB ("1.0 GB").  If it is larger than 1.0 MB ("1.0 MB"), it will
      be shown in MB.  Otherwise, it will be shown in bytes ("423413").

      @param xmlDom: DOM tree as from C{impl.createDocument()}.
      @param parentNode: Parent node to create child for.
      @param nodeName: Name of the new container node.
      @param byteQuantity: ByteQuantity object to put into the XML document

      @return: Reference to the newly-created node.
      """
      if byteQuantity is None:
         byteString = None
      elif byteQuantity.units == UNIT_KBYTES:
         byteString = "%s KB" % byteQuantity.quantity
      elif byteQuantity.units == UNIT_MBYTES:
         byteString = "%s MB" % byteQuantity.quantity
      elif byteQuantity.units == UNIT_GBYTES:
         byteString = "%s GB" % byteQuantity.quantity
      else:
         byteString = byteQuantity.quantity
      return addStringNode(xmlDom, parentNode, nodeName, byteString)
   _addByteQuantityNode = staticmethod(_addByteQuantityNode)


########################################################################
# Public functions
########################################################################

###########################
# executeAction() function
###########################

def executeAction(configPath, options, config):
   """
   Executes the split backup action.

   @param configPath: Path to configuration file on disk.
   @type configPath: String representing a path on disk.

   @param options: Program command-line options.
   @type options: Options object.

   @param config: Program configuration.
   @type config: Config object.

   @raise ValueError: Under many generic error conditions
   @raise IOError: If there are I/O problems reading or writing files
   """
   logger.debug("Executing split extended action.")
   if config.options is None or config.stage is None:
      raise ValueError("Cedar Backup configuration is not properly filled in.")
   local = LocalConfig(xmlPath=configPath)
   dailyDirs = findDailyDirs(config.stage.targetDir, SPLIT_INDICATOR)
   for dailyDir in dailyDirs:
      _splitDailyDir(dailyDir, local.split.sizeLimit, local.split.splitSize, 
                     config.options.backupUser, config.options.backupGroup)
      writeIndicatorFile(dailyDir, SPLIT_INDICATOR, config.options.backupUser, config.options.backupGroup)
   logger.info("Executed the split extended action successfully.")


##############################
# _splitDailyDir() function
##############################

def _splitDailyDir(dailyDir, sizeLimit, splitSize, backupUser, backupGroup):
   """
   Splits large files in a daily staging directory.

   Files that match INDICATOR_PATTERNS (i.e. C{"cback.store"},
   C{"cback.stage"}, etc.) are assumed to be indicator files and are ignored.
   All other files are split.

   @param dailyDir: Daily directory to encrypt
   @param sizeLimit: Size limit, in bytes
   @param splitSize: Split size, in bytes
   @param backupUser: User that target files should be owned by
   @param backupGroup: Group that target files should be owned by

   @raise ValueError: If the encrypt mode is not supported.
   @raise ValueError: If the daily staging directory does not exist.
   """
   logger.debug("Begin splitting contents of [%s]." % dailyDir)
   fileList = getBackupFiles(dailyDir)  # ignores indicator files
   limitBytes = float(convertSize(sizeLimit.quantity, sizeLimit.units, UNIT_BYTES))
   for path in fileList:
      size = float(os.stat(path).st_size)
      if size > limitBytes:
         _splitFile(path, splitSize, backupUser, backupGroup, removeSource=True)
   logger.debug("Completed splitting contents of [%s]." % dailyDir)


########################
# _splitFile() function
########################

def _splitFile(sourcePath, splitSize, backupUser, backupGroup, removeSource=False):
   """
   Splits the source file into chunks of the indicated size.

   The split files will be owned by the indicated backup user and group.  If
   C{removeSource} is C{True}, then the source file will be removed after it is
   successfully split.

   @param sourcePath: Absolute path of the source file to split
   @param splitSize: Encryption mode (only "gpg" is allowed)
   @param backupUser: User that target files should be owned by
   @param backupGroup: Group that target files should be owned by
   @param removeSource: Indicates whether to remove the source file

   @raise IOError: If there is a problem accessing, splitting or removing the source file.
   """
   cwd = os.getcwd()
   try:
      if not os.path.exists(sourcePath):
         raise ValueError("Source path [%s] does not exist." % sourcePath);
      dirname = os.path.dirname(sourcePath)
      filename = os.path.basename(sourcePath)
      prefix = "%s_" % filename
      bytes = int(convertSize(splitSize.quantity, splitSize.units, UNIT_BYTES))
      os.chdir(dirname) # need to operate from directory that we want files written to
      command = resolveCommand(SPLIT_COMMAND)
      args = [ "--verbose", "--numeric-suffixes", "--suffix-length=5", "--bytes=%d" % bytes, filename, prefix, ]
      (result, output) = executeCommand(command, args, returnOutput=True, ignoreStderr=False)
      if result != 0:
         raise IOError("Error [%d] calling split for [%s]." % (result, sourcePath))
      pattern = re.compile(r"(creating file `)(%s)(.*)(')" % prefix)
      match = pattern.search(output[-1:][0])
      value = int(match.group(3).strip())
      for index in range(0, value):
         path = "%s%05d" % (prefix, index)
         if not os.path.exists(path):
            raise IOError("After call to split, expected file [%s] does not exist." % path)
         changeOwnership(path, backupUser, backupGroup)
      if removeSource:
         if os.path.exists(sourcePath):
            try: 
               os.remove(sourcePath)
               logger.debug("Completed removing old file [%s]." % sourcePath)
            except: 
               raise IOError("Failed to remove file [%s] after splitting it." % (sourcePath))
   finally:
      os.chdir(cwd)
