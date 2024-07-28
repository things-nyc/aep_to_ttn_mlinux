##############################################################################
#
# Name: __init__.py
#
# Function:
#       Top-level package
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

# this must be first
from __future__ import annotations

# then the locally defined things
__author__ = """Terry Moore"""
__email__ = "tmm@mcci.com"

# get the version string
from . __version__ import __version__

# typing things
from typing import TYPE_CHECKING, Awaitable, Callable, List, Literal, Optional, Type, Union
