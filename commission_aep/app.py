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

    def get_api_url_no_token(self, param: str) -> str:
        return f"{self.url}{param}"

    def get_api_url_with_token(self, param: str) -> str:
        return f"{self.url}{param}?token={self.token}"

    def get_collection(self, param: str) -> Union[typing.Dict, None]:
        url = self.get_api_url_with_token(param)

        result = self._do_get("get collection", url=url)
        if 'result' in result:
            return result['result']
        return None

    def set_collection(self, param: str, newValue: dict) -> Union[typing.Dict, None]:
        """ set a collection named param """
        url = self.get_api_url_with_token(param)
        result = self._do_put(f"set collection {param}", url=url, data=newValue)
        return result

    def command(self, command: str, /, data:Any=None) -> Union[typing.Dict, None]:
        """ execute a command named 'command' """
        url = self.get_api_url_with_token(f"command/{command}")
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

    # login does not use token, so is special, calls _do_get()
    # directly.
    def login(self) -> bool:
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

    # get commissioning does not use token or user name,
    # so is special like login
    def get_commissioning(self) -> Union[typing.Dict, None]:
        logging.info("get commissioning info")
        if self.token != None:
            logging.error("already logged in")
            return None

        url = self.get_api_url_no_token("commissioning")
        result = self._do_get("fetch commissioning data", url)

        if 'error' in result:
            return None
        else:
            return result

    # set commissioning does not use token or user name,
    # so is special
    def set_commissioning(self, /, data: dict) -> Union[typing.Dict, None]:
        logging.info("set comissioning info")
        if self.token != None:
            logging.error("already logged in")
            return None

        url = self.get_api_url_no_token("commissioning")
        result = self._do_post("set commissioning info", url, data=data)

        if 'error' in result:
            return None
        else:
            return result
