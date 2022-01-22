from hotaru.players import Player

"""
{"type": "repeated", "start": actualMessage, "repeat": n}
{"type": "userjoin", "user": cmd[1]}
{"type": "userleft", "user": cmd[1]}
{"type": "userappend", "user": cmd[1]}
{"type": "su", "su": ""}
{"type": "msg", "from": author, "am": actualMessage["content"]}
"""


class RawMessage:
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
    def __init__(self, user: Player):
        self.user = user

    def repr(self):
        return {
            "type": "userappend",
            "user": self.user.name
        }


class UserJoin:
    def __init__(self, user: Player):
        self.user = user

    def repr(self):
        return {
            "type": "userjoin",
            "user": self.user.name
        }


class UserLeft:
    def __init__(self, user: Player):
        self.user = user

    def repr(self):
        return {
            "type": "userleft",
            "user": self.user.name
        }


class Su:
    def __init__(self, su: str):
        self.su = su

    def repr(self):
        return {
            "type": "su",
            "su": self.su
        }


class ShadowOfMessage:
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
