"""
This is just a holder for returning error codes and whatnot.
Because .close(code=ServerCodeDoesntExist()) makes more sense than .close(code=4000)
"""

import logging


def ServerCodeDoesntExist():
    logging.debug(f"exception: ServerCodeDoesntExist")
    return 4000 + 0


def ServerIsLocked():
    logging.debug(f"exception: ServerIsLocked")
    return 4000 + 1


def NameIsTaken():  # This one happens when you're trying to register and the name is taken
    logging.debug(f"exception: NameIsTaken")
    return 4000 + 2


def NameDoesntExist():  # This one happens when you supply a su code in the login
    logging.debug(f"exception: # NameDoesntExist")
    return 4000 + 3


def SuCodeMismatch():
    logging.debug(f"exception: SuCodeMismatch")
    return 4000 + 4


def SuAdminCodeMismatch():
    logging.debug(f"exception: SuAdminCodeMismatch")
    return 4000 + 5


def NamePropertyIsEmpty():
    logging.debug(f"exception: NamePropertyIsEmpty")
    return 4000 + 6


def RoomLimitReached():
    logging.debug(f"exception: RoomLimitReached")
    return 4000 + 7


def Overridden():
    logging.debug(f"exception: Overridden")
    return 4000 + 10


def BreakingApiChange():
    logging.debug(f"exception: BreakingApiChange")
    return 4000 + 19


def ServerClosing():
    logging.debug(f"exception: ServerClosing")
    return 4000 + 20

def BannedByRateLimit():
    return 4000 + 30
