from hotaru import exceptions
from hotaru.players import Player
import uuid
import random
import string


class PlayerPool:
    def __init__(self):
        self.name = 2
        self.players = {}

    def __setitem__(self, player_name, player):
        self.players[player_name] = player

    def __getitem__(self, player_name):
        return self.players[player_name]

    def __contains__(self, what):
        return what in self.players

    def list(self):
        return list(self.players.values())

    def count(self):
        return len(self.players)


class Server(Player):
    def __init__(self, code: str, limit: int):
        self.code = code
        self.name = 1
        self.su = str(uuid.uuid4())
        # suclient
        self.client = None
        # usr
        self.players = PlayerPool()
        # msg
        self.messages = []
        # publics
        self.messages_public = []
        self.next = 0
        # lck
        self.lock = False
        self.limit = limit

    def add_user(self, player: Player):
        if not player.name in self.players:
            self.players[player.name] = player
        else:
            pass  # TODO: throw error

    def has_player_safe(self, player_name):
        if not player_name in self.players:
            return None
        else:
            return self.players[player_name]

    def close_server(self):
        for player in self.players.list():
            player.client.close(exceptions.ServerClosing())
        self.client.close(exceptions.ServerClosing())


class ServerPool:
    def __init__(self):
        self.pool = {}

    def __contains__(self, what):
        return what in self.pool

    def _gen_code(self, prefix: str):
        x = "".join(random.choices(string.ascii_uppercase, k=4))
        if not prefix+x in self:
            return x
        else:
            return None

    def create_server(self, limit: int, prefix=""):
        code = None
        while not code:
            code = self._gen_code(prefix)

        self.pool[prefix+code] = Server(prefix+code, limit)
        return self.pool[prefix+code]

    def get_server_safe(self, server):
        if not server in self.pool:
            return None
        else:
            return self.pool[server]

    def free(self, server):
        if not server in self.pool:
            raise Exception
        else:
            self.pool.pop(server)
