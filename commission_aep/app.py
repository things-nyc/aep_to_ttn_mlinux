##############################################################################
#
# Name: app.py
#
# Function:
#       Toplevel App() class
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

#### imports ####
from __future__ import print_function
import argparse
import logging
import sys
import typing
import urllib3

Any = typing.Any
Union = typing.Union

from .constants import Constants
from .__version__ import __version__
from .aep_commissioning import AepCommissioning

##############################################################################
#
# The application class
#
##############################################################################

class App():
    def __init__(self):
        # load the constants
        self.constants = Constants()

        # configure urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # now parse the args
        options = self._parse_arguments()
        self.args = options

        logger = logging.getLogger()
        logger.handlers = []
        logger.addHandler(logging.StreamHandler())
        if options.debug:
            logger.setLevel('DEBUG')
        elif options.verbose:
            logger.setLevel('INFO')
        else:
            logger.setLevel('WARNING')

        self.log = logger

        # verbose: report the version.
        self.log.info("commission_aep v%s", __version__)

        self._initialize()
        self.log.info("App is initialized")
        return

    ##########################################################################
    #
    # The second-phase initializer
    #
    ##########################################################################

    def _initialize(self):
        self.aep = AepCommissioning(self.args)
        pass

    ##########################################################################
    #
    # The argument parser
    #
    ##########################################################################

    def _parse_arguments(self):
        parser = argparse.ArgumentParser(description="Set up and enable sshd on Conduit AEP using the configuration API")

        #	Debugging
        group = parser.add_argument_group("Debugging options")
        group.add_argument("-d", "--debug",
                        dest="debug", default=False,
                        action='store_true',
                        help="print debugging messages")
        group.add_argument("--nodebug",
                        dest="debug",
                        action='store_false',
                        help="do not print debugging messages")
        group.add_argument("-v", "--verbose",
                        dest="verbose", default=False,
                        action='store_true',
                        help="print verbose messages")
        group.add_argument("-n", "--noop",
                        dest="noop", default=False,
                        action='store_true',
                        help="Don't make changes, just list what we are going to do")

        #	Options
        group = parser.add_argument_group("Configuration options")
        group.add_argument("--username", "--user", "-U",
                        dest="username", default="mtadm",
                        help="Username to use to connect (default %(default)s)")
        group.add_argument("--password", "--pass", "-P",
                        dest="password", required=True,
                        help="Password to use to connect")
        group.add_argument("--address", "-A",
                        dest="address", default="192.168.2.1",
                        help="IP address of the conduit being commissioned (default %(default)s)")
        group.add_argument("-f", "--force",
                        dest="force", default=False,
                        action='store_true',
                        help="forcibly update the ssh setting and reboot, even if already set")
        group.add_argument("--skip-password", "-S",
                        dest="nopass", default=False,
                        action='store_true',
                        help="Assume username and password are already set"
                        )

        options = parser.parse_args()
        if options.debug:
            options.verbose = options.debug

        return options

    # return True if ssh needs to be changed
    def need_ssh_change(self, remoteAccess: dict) -> bool:
        ssh = remoteAccess['ssh']
        if ssh['enabled'] == True and \
           ssh['lan'] == True and \
           ssh['wan'] == False and \
           ssh['port'] == 22:
            return False
        else:
            return True

    ################
    # Set password #
    ################
    def set_password(self) -> bool:
        aep = self.aep
        options = self.args

        # prime the pump
        # if this fails, we assume it's already commissioned
        commissioning = aep.get_commissioning()
        if not commissioning:
            return True

        # if disabled, give up.
        if options.noop:
            return True

        # set up the data blob we'll be passing.
        data = {
            "username": options.username,
            "aasID": ""
        }

        # set the username, set the password, then confirm the password.
        for password in ["", options.password, options.password]:
            data["aasAnswer"] = password
            if "aasID" in commissioning:
                data["aasID"] = commissioning["aasID"]
            commissioning = aep.set_commissioning(data)
            if not commissioning:
                logging.warning("set_commissioning failed")
                return False

            if "aasType" in commissioning:
                aas_type = commissioning["aas_type"]
                aas_msg = commissioning["aas_msg"]
                if aas_type == "error":
                    logging.error("commissioning error: %s", aas_msg)
                    return False
                elif aas_type == "info":
                    logging.warning("%s", aas_msg)

        # if we get here, we succeeded
        logging.info("username and password successfully set")
        return True

    #######################################################
    # Enable SSH (assuming username and password are set) #
    #######################################################
    def enable_ssh(self) -> bool:
        aep = self.aep
        options = self.args

        if not aep.login():
            return False

        # restore to previous save
        result = aep.revert()

        if not result:
            logging.error("revert failed")
            return False

        # get the remote access state
        remoteAccess = aep.remoteAccess()
        if not remoteAccess:
            logging.error("could not read remoteAccess object")
            return False

        logging.debug("remoteAccess: %s", remoteAccess)

        sshChangeNeeded = self.need_ssh_change(remoteAccess)

        if not sshChangeNeeded:
            logging.info("ssh already enabled")
            if options.force:
                sshChangeNeeded = True

        # modify ssh settings
        if sshChangeNeeded:
            remoteAccess['ssh']['enabled'] = True
            remoteAccess['ssh']['lan'] = True
            remoteAccess['ssh']['wan'] = False
            remoteAccess['ssh']['port'] = 22

            if not options.noop:
                result = aep.remoteAccess(remoteAccess)
                if result == None:
                    logging.error("failed to set ssh in remoteAccess")
                    return False

                result = aep.save()
                if result == None:
                    logging.error("failed to save state")
                    return False

                result = aep.restart()
                if result == None:
                    logging.error("failed to trigger a reboot")
                    return False
            else:
                logging.info("skipping update of remoteAccess")

        # Success!
        return True

    #################################
    # Run the app and return status #
    #################################
    def run(self) -> int:
        aep = self.aep
        options = self.args

        if not options.nopass:
            if not self.set_password():
                return 1

        if not self.enable_ssh():
            return 1

        return 0
