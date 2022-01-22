def ServerCodeDoesntExist():
    return 4000 + 0


def ServerIsLocked():
    return 4000 + 1


def NameIsTaken():  # This one happens when you're trying to register and the name is taken
    return 4000 + 2


def NameDoesntExist():  # This one happens when you supply a su code in the login
    return 4000 + 3


def SuCodeMismatch():
    return 4000 + 4


def SuAdminCodeMismatch():
    return 4000 + 5


def NamePropertyIsEmpty():
    return 4000 + 6


def RoomLimitReached():
    return 4000 + 7


def Overridden():
    return 4000 + 10


def ServerClosing():
    return 4000 + 20
