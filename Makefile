##############################################################################
#
# Module: Makefile
#
# Purpose:
#	Procedures for this directory
#
# Copyright notice and license:
#   See LICENSE.md in this directory.
#
# Author:
#   Terry Moore   July 2024
#
##############################################################################

# figure out where Python virtual env executable artifacts live on this system
ifeq ($(OS),Windows_NT)
 VENV_SCRIPTS=Scripts
else
 VENV_SCRIPTS=bin
endif

# based on this, set the path to the bash activate script.
ACTIVATE=${VENV_SCRIPTS}/activate

# the default python
PYTHON=python3

# the python for VENVs
PYTHON_VENV=python

#
# Default target: print help.
#
help:
	@printf "%s\n" \
		"This Makefile contains the following targets" \
		"" \
		"* make help -- prints this message" \
		"* make build -- builds the app (in dist)" \
		"* make venv -- sets up the virtual env for development" \
		"* make clean -- get rid of build artifacts" \
		"* make distclean -- like clean, but also removes distribution directory" \
		"" \
		"On this system, virtual env scripts are in {envpath}/${VENV_SCRIPTS}"

#
# targets for building releases:
#    .buildenv creates the first stage build environment (where we can install build)
#    build actually creates release files.
#
.buildenv:
	$(PYTHON) -m venv .buildenv
	. .buildenv/$(ACTIVATE) && \
		$(PYTHON_VENV) -m pip install build

build:	.buildenv
	. .buildenv/$(ACTIVATE) && $(PYTHON_VENV) -m build
	@printf "%s\n" "distribution files are in the dist directory:" && ls dist

#
# targets for local development:
#    .venv creates the virtual environment and installs requirements
#    venv does the same, but tells you how to use the venv.
#
.venv:
	$(PYTHON) -m venv .venv
	. .venv/$(ACTIVATE) && $(PYTHON_VENV) -m pip install -r requirements.txt

venv:	.venv
	@printf "%s\n" \
		"Virtual environment created in .venv." \
		"" \
		"To activate in bash, say:" \
		"    . .venv/${ACTIVATE}" \
		""
	@if [ "${PYTHON_VENV}" != "${PYTHON}" ]; then \
		printf "%s\n" \
			"Then be sure to run the app using ${PYTHON_VENV} (not ${PYTHON})" \
			"" \
		; \
	fi

#
# maintenance targets
#
clean:
	rm -rf .buildenv .venv *.egg-info */__pycache__

distclean:	clean
	rm -rf dist

#### end of file ####
