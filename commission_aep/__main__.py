##############################################################################
#
# Name: __main__.py
#
# Function:
#       Entry point for main command
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

#### imports ####
import sys

from . import app as app
from .constants import Constants

##############################################################################
#
# The main program
#
##############################################################################

def main_inner() -> int:
    global gApp

    # create an app object
    try:
        gApp = app.App()
    except Exception as e:
        print("app creation failed:", e)
        raise

    gApp.log.debug("launching app")
    return gApp.run()

def main() -> int:
    try:
        result = main_inner()
        if result != 0:
            gApp.log.error("failure, exit with status %d", result)
        else:
            gApp.log.info("success, exit with status 0")
        return result
    except KeyboardInterrupt:
        print("Exited due to keyboard interrupt")
        return 1

if __name__ == '__main__':
    sys.exit(main())
