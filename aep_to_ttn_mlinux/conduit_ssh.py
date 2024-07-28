##############################################################################
#
# Name: aep_ssh.py
#
# Function:
#       Toplevel AepSsh() class, provides APIs for ssh conrol of
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
import typing

Any = typing.Any
Union = typing.Union

import warnings
with warnings.catch_warnings():
   warnings.filterwarnings("ignore", message='.*cryptography')
   import fabric

from .constants import Constants

##############################################################################
#
# The Conduit SSH API
#
##############################################################################

class ConduitSsh():
    def __init__(self, options: Any):
        self.options = options
        self.connection = fabric.Connection(    
                            host=options.address,
                            user=options.username,
                            connect_kwargs={
                                "password": options.password,
                                "timeout": 3
                            }
                            )
        self.logger = Logging.getLogger(__name__)
        pass

    class Error(Exception):
        """ this is the Exception thrown by class AepSsh """
        pass

    # return TRUE if we can reach via SSH
    def ping(self, /, timeout: Union[int, None]=None) -> bool:
        self.logger.info("ping ssh")
        connection = self.connection

        if timeout != None:
            connection.connect_timeout = timeout

        try:
            _ = connection.run("echo ping", hide=True, timeout=5)
            return True
        except Exception as error:
            return False

    def sudo(self, command: str, /, **sudo_kwargs) -> bool:
        self.logger.info("sudo")
        connection = self.connection
        options = self.options

        try:
            result = connection.sudo(
                    command, 
                    password=options.password,
                    dry=options.noop,
                    **sudo_kwargs
                    )
            self.logger.debug("sudo results: %s", result)
            return True
        except Exception as error:
            self.logger.error("sudo error", exc_info=error, stack_info=True)
            return False
