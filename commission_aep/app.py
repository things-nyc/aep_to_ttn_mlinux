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
import requests
import sys
import typing
import urllib3

Any = typing.Any
Union = typing.Union

from .constants import Constants
from .__version__ import __version__

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
        self.aep = Aep(self.args)
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
        group.add_argument("-f", "--force",
                        dest="force", default=False,
                        action='store_true',
                        help="forcibly update the ssh setting and reboot, even if already set")

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

    #################################
    # Run the app and return status #
    #################################
    def run(self) -> int:
        aep = self.aep
        options = self.args

        if not aep.login():
            return 1

        # restore to previous save
        result = aep.revert()

        if not result:
            logging.error("revert failed")
            return 1

        # get the remote access state
        remoteAccess = aep.remoteAccess()
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
                    return 1

                result = aep.save()
                if result == None:
                    logging.error("failed to save state")
                    return 1

                result = aep.restart()
                if result == None:
                    logging.error("failed to trigger a reboot")
                    return 1
            else:
                logging.info("skipping update of remoteAccess")

        # save the settings
        return 0

##############################################################################
#
# The AEP Config API
#
##############################################################################

class Aep():
    def __init__(self, options: Any):
        self.options = options
        self.session = requests.Session()
        self.url = "https://{options.address}/api/".format(options=options)
        self.token = None
        pass

    class Error(Exception):
        """ this is the Exception thrown for tracker errors """
        pass

    def _do_get(self, description: str, url: str) -> dict:
        try:
            logging.debug("%s: GET %s", description, url)
            response = self.session.get(url, verify=False)
            response.raise_for_status()
            result = response.json()
            logging.debug("%s GET response: %s", description, result)
        except requests.exceptions.RequestException as error:
            logging.debug("%s error: %s", description, error)
            result = { 'error': error }

        return result

    def _do_post(self, description: str, url: str, data: Any = None) -> dict:
        try:
            logging.debug("%s: POST %s", description, url)
            response = self.session.post(url, verify=False, json=data)
            response.raise_for_status()
            result = response.json()
            logging.debug("%s: POST result: %s", description, result)
        except requests.exceptions.RequestException as error:
            logging.debug("%s POST error: %s", description, error)
            result = { 'error': error }

        return result

    def _do_put(self, description: str, /, url: str, data: Any = None) -> dict:
        try:
            logging.debug("%s: PUT %s", description, url)
            response = self.session.put(url, verify=False, json=data)
            response.raise_for_status()
            result = response.json()
            logging.debug("%s: PUT response: %s", description, result)
        except requests.exceptions.RequestException as error:
            logging.debug("%s PUT error: %s", description, error)
            result = { 'error': error }

        return result

    def login(self) -> Any:
        logging.info("log in")
        if self.token != None:
            return True
        options = self.options
        url = f"{self.url}login?username={options.username}&password={options.password}"
        result = self._do_get("logging in", url)
        if 'result' in result and 'token' in result['result']:
            self.token = result['result']['token']
            return True
        logging.error("login failed: %s", result)
        return False

    def get_api_url(self, param: str) -> str:
        return f"{self.url}{param}?token={self.token}"

    def get_collection(self, param: str) -> Union[typing.Dict, None]:
        url = self.get_api_url(param)

        result = self._do_get("get collection", url=url)
        if 'result' in result:
            return result['result']
        return None

    def set_collection(self, param: str, newValue: dict) -> Union[typing.Dict, None]:
        """ set a collection named param """
        url = self.get_api_url(param)
        result = self._do_put(f"set collection {param}", url=url, data=newValue)
        return result

    def command(self, command: str, /, data:Any=None) -> Union[typing.Dict, None]:
        """ execute a command named 'command' """
        url = self.get_api_url(f"command/{command}")
        if data == None:
            result = self._do_post(f"do_command {command}", url=url)
        else:
            result = self._do_post(f"do command {command}", url=url, data=data)

        if 'error' in result:
            return None
        else:
            return result

    #### specific AEP commands
    def revert(self):
        logging.info("revert gateway state to saved")
        return self.command("revert")

    def remoteAccess(self, /, data: Any = None) -> Union[typing.Dict, None]:
        if data == None:
            logging.info("get remoteAccess collection")
            return self.get_collection("remoteAccess")
        else:
            logging.info("set remoteAccess collection")
            return self.set_collection("remoteAccess", newValue=data)

    def save(self):
        logging.info("save gateway state")
        return self.command("save")

    def restart(self):
        logging.info("reboot gateway (this takes a while)")
        return self.command("restart")
