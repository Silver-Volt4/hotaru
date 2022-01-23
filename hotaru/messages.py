from hotaru.players import Player

"""
Holder classes for all message types we currently support.
"""


class RawMessage:
    """
    Class for user-sent messages, these are always
    from someone else, not Hotaru itself
    """

    def __init__(self, from_: Player, message_content):
        self.from_ = from_
        self.message_content = message_content

    def repr(self):
        return {
            "type": "msg",
            "from": self.from_.name,
            "am": self.message_content
        }


class UserAppend:
    """
    Sent to the owner when a player enters the game for the first time,
    their name should be appended to some kind of dictionary
    on the server owner's end
    """

    def __init__(self, user: Player):
        self.user = user

    def repr(self):
        return {
            "type": "userappend",
            "user": self.user.name
        }


class UserJoin:
    """
    Sent to the owner when an already registered player joins the game back,
    presumably after being disconnected or when switching devices
    """

    def __init__(self, user: Player):
        self.user = user

    def repr(self):
        return {
            "type": "userjoin",
            "user": self.user.name
        }


class UserLeft:
    """
    Sent to the owner when an already registered player disconnects abnormally,
    presumably after network problems
    """

    def __init__(self, user: Player):
        self.user = user

    def repr(self):
        return {
            "type": "userleft",
            "user": self.user.name
        }


class Su:
    """
    Sent to every newly registered player, this code is used for
    authentication later on, for instance when reconnecting
    """

    def __init__(self, su: str):
        self.su = su

    def repr(self):
        return {
            "type": "su",
            "su": self.su
        }


class ShadowOfMessage:
    """
    This type of message is never sent directly, rather, it's a part
    of a "repeat" packet. They are messages sent by a player to Hotaru.

    Example usage would be in a chat app, where normal messages
    were sent by other players, and shadows were sent by you.
    One could rebuild the chat log like this.
    """

    def __init__(self, to, content):
        self.to = to
        self.content = content

    def repr(self):
        return {
            "type": "shadow",
            "shadow": {
                "to": self.to.name,
                "content": self.content
            }
        }
