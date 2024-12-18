##############################################################################
#
# Name: aep_commissioning.py
#
# Function:
#       Toplevel AepCommissioning() class, provides APIs for talking to
#       a controlled Conduit.
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
import logging as Logging
import requests
import typing

Any = typing.Any
Union = typing.Union

from .constants import Constants

##############################################################################
#
# The AEP Commissioning API
#
##############################################################################

class AepCommissioning():
    def __init__(self, options: Any):
        self.options = options
        self.session = requests.Session()
        self.url = "https://{options.address}/api/".format(options=options)
        self.token = None
        self.logger = Logging.getLogger(__name__)
        pass

    class Error(Exception):
        """ this is the Exception thrown for AEP Commissioning errors """
        pass

    def _do_get(self, description: str, url: str) -> dict:
        logger = self.logger
        try:
            logger.debug("%s: GET %s", description, url)
            response = self.session.get(url, verify=False)
            response.raise_for_status()
            result = response.json()
            logger.debug("%s GET response: %s", description, result)
        except requests.exceptions.RequestException as error:
            logger.debug("%s error: %s", description, error)
            result = { 'error': error }

        return result

    def _do_post(self, description: str, url: str, data: Any = None) -> dict:
        logger = self.logger
        try:
            logger.debug("%s: POST %s", description, url)
            response = self.session.post(url, verify=False, json=data)
            response.raise_for_status()
            result = response.json()
            logger.debug("%s: POST result: %s", description, result)
        except requests.exceptions.RequestException as error:
            logger.debug("%s POST error: %s", description, error)
            result = { 'error': error }

        return result

    def _do_put(self, description: str, /, url: str, data: Any = None) -> dict:
        logger = self.logger
        try:
            logger.debug("%s: PUT %s", description, url)
            response = self.session.put(url, verify=False, json=data)
            response.raise_for_status()
            result = response.json()
            logger.debug("%s: PUT response: %s", description, result)
        except requests.exceptions.RequestException as error:
            logger.debug("%s PUT error: %s", description, error)
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
        self.logger.info("revert gateway state to saved")
        return self.command("revert")

    def remoteAccess(self, /, data: Any = None) -> Union[typing.Dict, None]:
        if data == None:
            self.logger.info("get remoteAccess collection")
            return self.get_collection("remoteAccess")
        else:
            self.logger.info("set remoteAccess collection")
            return self.set_collection("remoteAccess", newValue=data)

    def systemObject(self, /, data: Union[typing.Dict, None] = None) -> Union[typing.Dict, None]:
        if data == None:
            self.logger.info("get system collection")
            return self.get_collection("system")
        else:
            self.logger.info("set system collection")
            return self.set_collection("system", newValue=data)

    def save(self):
        self.logger.info("save gateway state")
        return self.command("save")

    def restart(self):
        self.logger.info("reboot gateway (this takes a while)")
        return self.command("restart")

    # login does not use token, so is special, calls _do_get()
    # directly.
    def login(self) -> bool:
        self.logger.info("log in")
        if self.token != None:
            return True
        options = self.options
        url = f"{self.url}login?username={options.username}&password={options.password}"
        result = self._do_get("logging in", url)
        if 'result' in result and 'token' in result['result']:
            self.token = result['result']['token']
            return True
        self.logger.error("login failed: %s", result)
        return False

    # get commissioning does not use token or user name,
    # so is special like login
    def get_commissioning(self) -> Union[typing.Dict, None]:
        self.logger.info("get commissioning info")
        if self.token != None:
            self.logger.error("already logged in")
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
        self.logger.info("set comissioning info")
        if self.token != None:
            self.logger.error("already logged in")
            return None

        url = self.get_api_url_no_token("commissioning")
        result = self._do_post("set commissioning info", url, data=data)

        if 'error' in result:
            return None
        else:
            return result
