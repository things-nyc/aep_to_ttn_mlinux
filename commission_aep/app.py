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
import pathlib
import sys
import time
import typing
import urllib3

Any = typing.Any
Union = typing.Union

from .constants import Constants
from .__version__ import __version__
from .aep_commissioning import AepCommissioning
from .conduit_ssh import ConduitSsh

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

        logging.basicConfig()
        logger = logging.getLogger(__name__)
        #logger.handlers = []
        #logger.addHandler(logging.StreamHandler())
        if options.debug:
            logger.setLevel('DEBUG')
        elif options.verbose:
            logger.setLevel('INFO')
        else:
            logger.setLevel('WARNING')

        self.logger = logger

        # verbose: report the version.
        logger.info("commission_aep v%s", __version__)

        self._initialize()
        logger.info("App is initialized")
        return

    ##########################################################################
    #
    # The second-phase initializer
    #
    ##########################################################################

    def _initialize(self):
        self.aep = AepCommissioning(self.args)
        self.ssh = ConduitSsh(self.args)
        pass

    ##########################################################################
    #
    # The argument parser
    #
    ##########################################################################

    def _parse_arguments(self):
        parser = argparse.ArgumentParser(
            prog="commission_aep",
            description="Set up and enable sshd on Conduit AEP using the configuration API"
            )

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
        group.add_argument("-n", "--noop", "--dry-run",
                        dest="noop", default=False,
                        action='store_true',
                        help="Don't make changes, just list what we are going to do")
        parser.add_argument(
                        "--version",
                        action='version',
                        help="Print version and exit",
                        version="%(prog)s v"+__version__
                        )

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
        # https://ttni.tech/mlinux/images/mtcdt/5.3.31/ttni-base-image-mtcdt-upgrade.bin
        group.add_argument("--image",
                        dest="image_file", default="/tmp/ttni-base-image-mtcdt-upgrade.bin",
                        help="path to image to be downloaded"
                        )
        group.add_argument("--reboot_time",
                        dest="reboot_time", default=5*60,
                        type=int,
                        action="store",
                        help="how long to wait for reboots, in seconds (default %(default)s)"
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
        logger = self.logger

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
                logger.warning("set_commissioning failed")
                return False

            if "aasType" in commissioning:
                aas_type = commissioning["aas_type"]
                aas_msg = commissioning["aas_msg"]
                if aas_type == "error":
                    logger.error("commissioning error: %s", aas_msg)
                    return False
                elif aas_type == "info":
                    logger.warning("%s", aas_msg)

        # if we get here, we succeeded
        logger.info("username and password successfully set")
        return True

    #######################################################
    # Enable SSH (assuming username and password are set) #
    #######################################################
    def enable_ssh(self) -> bool:
        aep = self.aep
        options = self.args
        logger = self.logger

        if not aep.login():
            return False

        # restore to previous save
        result = aep.revert()

        if not result:
            logger.error("revert failed")
            return False

        # get the remote access state
        remoteAccess = aep.remoteAccess()
        if not remoteAccess:
            logger.error("could not read remoteAccess object")
            return False

        logger.debug("remoteAccess: %s", remoteAccess)

        sshChangeNeeded = self.need_ssh_change(remoteAccess)

        if not sshChangeNeeded:
            logger.info("ssh already enabled")
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
                    logger.error("failed to set ssh in remoteAccess")
                    return False

                result = aep.save()
                if result == None:
                    logger.error("failed to save state")
                    return False

                result = aep.restart()
                if result == None:
                    logger.error("failed to trigger a reboot")
                    return False

                # wait for ping to fail
                nPings = 1
                while True:
                    if not self.ssh.ping():
                        break
                    time.sleep(1)
                    nPings += 1

                logger.info("ssh unavailable on ping {ping}".format(ping=nPings))

            else:
                logger.info("skipping update of remoteAccess")

        # Success!
        return True

    # copy image to Conduit
    def copy_image(self) -> bool:
        c = self.ssh.connection
        options = self.args
        infile = pathlib.Path(options.image_file)
        logger = self.logger

        if not infile.exists():
            logger.error("image_file not found: %s", infile)

        if options.noop:
            return True

        try:
            logger.info("put image file: %s", infile)
            _ = c.put(infile, remote="/tmp/firmware.bin")
        except Exception as error:
            logger.error("failed to put image file: {error}".format(error=error))
            return False

        return True

    # apply image
    def apply_image(self) -> bool:
        self.logger.info("apply_image")
        return self.ssh.sudo(
                    "/usr/sbin/mlinux-firmware-upgrade /tmp/firmware.bin",
                    echo=True
                    )

    ################################
    # Check whether SSH is enabled #
    ################################
    def check_ssh_enabled(self, /, timemout: Union[int, None] = None) -> bool:
        c = self.ssh
        logger = self.logger

        if c.ping():
            logger.info("ssh to %s is working", self.args.address)
            return True
        else:
            logger.error("ssh to %s is not working", self.args.address)
            return False

    #############################
    # Loop until SSH is enabled #
    #############################
    def await_ssh_available(self, /, timeout:int = 10, progress:bool = False) -> bool:
        c = self.ssh
        logger = self.logger

        begin = time.time()
        while time.time() - begin < self.args.reboot_time:
            print('.', end='', flush=True)
            if c.ping():
                print()
                logger.info("ssh available after {t} seconds".format(t=time.time() - begin))
                return True
            time.sleep(1)
        return False

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

        if not self.check_ssh_enabled():
            if not self.await_ssh_available(options.reboot_time):
                return 1

        # copy the image
        if not self.copy_image():
            return 1

        # apply the image
        if not self.apply_image():
            return 1

        return 0
