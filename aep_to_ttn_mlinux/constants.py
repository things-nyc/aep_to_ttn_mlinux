##############################################################################
#
# Name: constants.py
#
# Function:
#       Class for the immutable constants for this app
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

#### imports ####
import re

#### The Constants class
class Constants:
        __slots__ = ()  # prevent changes

        DEFAULT_IP = "192.168.2.1"      # default address of Conduit

        # default time to wait for AEP to reboot.
        DEFAULT_AEP_REBOOT_TIME_MAX = 600

        # default image name
        DEFAULT_MLINUX_IMAGE_PATTERN = "/tmp/ttni-base-image-{product_type}-upgrade.bin"

        DEFAULT_AEP_USERNAME = "mtadm"

### end of file ###
