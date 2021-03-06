# vim: set ft=make:
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
#              C E D A R
#          S O L U T I O N S       "Software done right."
#           S O F T W A R E
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Author   : Kenneth J. Pronovici <pronovic@ieee.org>
# Language : Make
# Project  : Cedar Backup, release 2
# Purpose  : Makefile used for building the Cedar Backup manual.
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

########
# Notes
########

# This Makefile was originally taken from the Subversion project's book
# (http://svnbook.red-bean.com/) and has been substantially modifed (almost
# completely rewritten) for use with Cedar Backup.
#
# The original Makefile was (c) 2000-2004 CollabNet (see CREDITS).


########################
# Programs and commands
########################

CP                       = cp
INSTALL                  = install
MKDIR                    = mkdir
RM                       = rm
XSLTPROC                 = xsltproc
W3M                      = w3m


############
# Locations
############

INSTALL_DIR              = ../doc/manual

XSL_DIR                  = ../util/docbook
STYLES_CSS               = $(XSL_DIR)/styles.css
XSL_FO                   = $(XSL_DIR)/fo-stylesheet.xsl
XSL_HTML                 = $(XSL_DIR)/html-stylesheet.xsl
XSL_CHUNK                = $(XSL_DIR)/chunk-stylesheet.xsl

MANUAL_TOP               = .
MANUAL_DIR               = $(MANUAL_TOP)/src
MANUAL_CHUNK_DIR         = $(MANUAL_DIR)/chunk
MANUAL_HTML_TARGET       = $(MANUAL_DIR)/manual.html
MANUAL_CHUNK_TARGET      = $(MANUAL_CHUNK_DIR)/index.html  # index.html is created last
MANUAL_TEXT_TARGET       = $(MANUAL_DIR)/manual.txt
MANUAL_XML_SOURCE        = $(MANUAL_DIR)/book.xml
MANUAL_ALL_SOURCE        = $(MANUAL_DIR)/*.xml
MANUAL_HTML_IMAGES       = $(MANUAL_DIR)/images/html/*.png


#############################################
# High-level targets and simple dependencies
#############################################

all: manual-html manual-chunk 

install: install-manual-html install-manual-chunk install-manual-text

clean: 
	-@$(RM) -f $(MANUAL_HTML_TARGET) $(MANUAL_FO_TARGET) $(MANUAL_TEXT_TARGET)
	-@$(RM) -rf $(MANUAL_CHUNK_DIR)

$(INSTALL_DIR):
	$(INSTALL) --mode=775 -d $(INSTALL_DIR)


###################
# HTML build rules
###################

manual-html: $(MANUAL_HTML_TARGET)

$(MANUAL_HTML_TARGET): $(MANUAL_ALL_SOURCE)
	$(XSLTPROC) --output $(MANUAL_HTML_TARGET) $(XSL_HTML) $(MANUAL_XML_SOURCE)

install-manual-html: $(MANUAL_HTML_TARGET) $(INSTALL_DIR)
	$(INSTALL) --mode=775 -d $(INSTALL_DIR)/images
	$(INSTALL) --mode=664 $(MANUAL_HTML_TARGET) $(INSTALL_DIR)
	$(INSTALL) --mode=664 $(STYLES_CSS) $(INSTALL_DIR)
	$(INSTALL) --mode=664 $(MANUAL_HTML_IMAGES) $(INSTALL_DIR)/images


###########################
# Chunked HTML build rules
##################*########

manual-chunk: $(MANUAL_CHUNK_TARGET)

# The trailing slash in the $(XSLTPROC) command is essential, so that xsltproc will output pages to the dir
$(MANUAL_CHUNK_TARGET): $(MANUAL_ALL_SOURCE) $(STYLES_CSS) $(MANUAL_HTML_IMAGES)
	$(MKDIR) -p $(MANUAL_CHUNK_DIR)
	$(MKDIR) -p $(MANUAL_CHUNK_DIR)/images
	$(XSLTPROC) --output $(MANUAL_CHUNK_DIR)/ $(XSL_CHUNK) $(MANUAL_XML_SOURCE)
	$(CP) $(STYLES_CSS) $(MANUAL_CHUNK_DIR)
	$(CP) $(MANUAL_HTML_IMAGES) $(MANUAL_CHUNK_DIR)/images

install-manual-chunk: $(MANUAL_CHUNK_TARGET) $(INSTALL_DIR)
	$(INSTALL) --mode=775 -d $(INSTALL_DIR)/images
	$(INSTALL) --mode=664 $(MANUAL_CHUNK_DIR)/*.html $(INSTALL_DIR)
	$(INSTALL) --mode=664 $(STYLES_CSS) $(INSTALL_DIR)
	$(INSTALL) --mode=664 $(MANUAL_HTML_IMAGES) $(INSTALL_DIR)/images


###################
# Text build rules
###################

manual-text: manual-html $(MANUAL_TEXT_TARGET)

$(MANUAL_TEXT_TARGET):
	$(W3M) -dump -cols 80 $(MANUAL_HTML_TARGET) > $(MANUAL_TEXT_TARGET)

install-manual-text: $(MANUAL_TEXT_TARGET) $(INSTALL_DIR)
	$(INSTALL) --mode=664 $(MANUAL_TEXT_TARGET) $(INSTALL_DIR)


