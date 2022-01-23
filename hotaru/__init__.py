import tornado.escape
import tornado.template
import tornado.web
import tornado.websocket

from hotaru import messages
from hotaru import exceptions
from hotaru.servers import ServerPool
from hotaru.players import Player

import logging
import json


class Command:
    """
    Class for holding information about the user
    that connected / disconnected / sent a message
    """

    def __init__(self):
        self.server = None
        self.player = None
        self.su = None

        self.su_admin = None
        self.join_request = None


class Hotaru(tornado.web.Application):
    """
    Main object for the Tornado server.
    """

    def __init__(self, logging, inspect):
        # A reference to this object is passed to all handlers.
        # The ServerPool object holds Server objects, which hold Player objects.
        # This allows to have separate ServerPools on different endpoints,
        # if that is desired.
        self.pool = ServerPool()

        handlers = [
            ("/ws/(.*)", HotaruWebsocket,
             {"pool": self.pool, "log": logging}),
            ("/hotaru/(.*)",   HotaruCommands,
             {"pool": self.pool, "log": logging}),
        ]
        if inspect:
            handlers.append(
                ("/inspect(.*)", HotaruInspector,
                 {"pool": self.pool, "log": logging})
            )
        super().__init__(handlers)


class HotaruInspector(tornado.web.RequestHandler):
    """
    Object for the optional Hotaru inspector.
    Currently lacks authentication, but it can be turned off.
    """

    def initialize(self, pool):
        self.pool = pool
        self.loader = tornado.template.Loader("./inspector")

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def get(self, cmd):
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        cmd = cmd.split("/")[1:]

        if cmd[0] == "":
            s = list(self.pool.pool.values())
            self.write(self.loader.load(
                "home.html").generate(a="x", servers=s))

        else:
            serv = self.pool.get_server_safe(cmd[0])
            if serv:
                pass
            else:
                self.set_status(404)
                self.write("Not found")


class HotaruCommands(tornado.web.RequestHandler):
    """
    Object for the /hotaru endpoint.
    This is where apps ask for new servers, deleting them...
    """

    def initialize(self, pool):
        self.pool = pool

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def get(self, cmd):
        # This might not be the best way to do it, but whatever...
        cmd = cmd.split("/")

        if cmd[0] == "create_room":
            # Expected structure:
            # [1] = max limit of players as an integer, anything negative means infinite, defaults to -1
            # [2] = code prefix, defaults to none
            limit = 0
            try:
                limit = int(cmd[1])
                if limit < 0:
                    limit = -1
            except:
                limit = -1

            prefix = ""
            if len(cmd) >= 3:
                prefix = cmd[2]

            server = self.pool.create_server(limit, prefix)
            game_code = server.code
            su = server.su
            self.write("\n".join((game_code[-4:], su)))

        if cmd[0] == "close_room":
            # Expected structure:
            # [1] = server code
            # [2] = su code for that server
            server = self.pool.has_server_safe(cmd[1])
            if server:
                if server.su == cmd[2]:
                    server.close_server()
                    self.pool.free(server.code)
                    self.set_status(200)
                    self.write("OK")
                else:
                    self.set_status(401)
                    self.write("Unauthorized")
            else:
                self.set_status(404)
                self.write("Not found")


class HotaruWebsocket(tornado.websocket.WebSocketHandler):
    """
    Main object for the WebSocket endpoint itself.
    This is where actual communication happens.
    """

    def initialize(self, pool):
        self.pool = pool

    def check_origin(self, origin):
        # VERY UNSAFE. This should get a tweak as soon as possible!!!
        return True

    def get_compression_options(self):
        # Non-None enables compression with default options
        return {}

    def parse_cmd(self, cmd):
        # Here, we create a command object for the respective access URL
        # Hotaru depends on it in a sense

        cmd[1] = tornado.escape.url_unescape(cmd[1], plus=False)

        command = Command()
        if len(cmd) == 4:  # Room admin connecting
            command.server = self.pool.get_server_safe(cmd[0])
            command.su_admin = cmd[3]
            command.player = command.server
        if len(cmd) == 3:  # Player REconnecting
            command.server = self.pool.get_server_safe(cmd[0])
            command.su = cmd[2]
            if command.server:
                command.player = command.server.has_player_safe(cmd[1])
        if len(cmd) == 2:  # Player register
            command.server = self.pool.get_server_safe(cmd[0])
            command.join_request = cmd[1]
            if command.server:
                command.player = command.server.has_player_safe(cmd[1])

        # len(cmd) == 1 should never happen.

        return command

    def open(self, client):
        cmd = self.parse_cmd(self.request.path.split("/")[2:])

        # Check for errors in the connection and kick the client if necessary

        if not cmd.server:
            self.close(code=exceptions.ServerCodeDoesntExist())

        elif cmd.join_request and cmd.server.lock:
            self.close(code=exceptions.ServerIsLocked())

        elif cmd.join_request and cmd.server.players.count() == cmd.server.limit:
            self.close(code=exceptions.RoomLimitReached())

        # In this section, we might have got a player trying to register
        elif cmd.join_request and not cmd.server.lock:

            if cmd.join_request and cmd.player:
                self.close(code=exceptions.NameIsTaken())

            # If the name property isn't empty, we're safe
            elif cmd.join_request != "":
                p = Player(cmd.join_request, self)
                cmd.server.add_user(p)
                cmd.player = p
                su_message = messages.Su(p.su)
                p.write_message(su_message)

                for pb in cmd.server.messages_public:
                    p.messages.append(pb)
                    p.next += 1

                append = messages.UserAppend(p)
                cmd.server.write_message(append)

            else:
                self.close(code=exceptions.NamePropertyIsEmpty())

        # In this section, we might have got a registered player trying to reconnect
        elif cmd.su:
            if not cmd.player:
                self.close(code=exceptions.NameDoesntExist())

            if cmd.player.su != cmd.su:
                self.close(code=exceptions.SuCodeMismatch())

            # The player name exists and the code is correct
            if cmd.player.su == cmd.su:
                try:
                    cmd.player.client.close(code=exceptions.Overridden())
                except:
                    pass
                cmd.player.client = self

                join = messages.UserJoin(cmd.player)
                cmd.server.write_message(join)

        # In this section, we might have got the server creator connecting
        elif cmd.su_admin:
            if cmd.server.su != cmd.su_admin:
                self.close(code=exceptions.SuAdminCodeMismatch())

            # The code checks out
            else:
                try:
                    cmd.server.client.close(code=exceptions.Overridden())
                except:
                    pass
                cmd.server.client = self

    # We notify the server owner about the disconnection
    def on_connection_close(self):
        cmd = self.parse_cmd(self.request.path.split("/")[2:])
        if self.close_code:
            if self.close_code != 1000 and self.close_code < 4000:
                if cmd.player:
                    left = messages.UserLeft(cmd.player)
                    cmd.server.write_message(left)

    # Responsible for delivering messages
    def message_send_shorthand(self, cmd, actual_message):
        if actual_message["to"] == 1:
            recipient = cmd.server
        elif actual_message["to"] == 2:
            recipient = cmd.server.players
        else:
            recipient = cmd.server.has_player_safe(actual_message["to"])

        msg = messages.RawMessage(cmd.player, actual_message["content"])
        cmd.player.sends_message(recipient, msg)

        if actual_message["to"] == 2:
            cmd.player.sends_message(cmd.server, msg, True)
            cmd.server.messages_public.append(msg)

    # Fires when a WS packet is received
    def on_message(self, message, *args):

        # We discard any packet with a length less than or equal to 1.
        # This is for Heroku, it likes to disconnect those that it deems inactive.
        # I usually counter this by sending a whitespace every 5 seconds or so
        if len(message) <= 1:
            return

        cmd = self.parse_cmd(self.request.path.split("/")[2:])

        message_command = message.split(" ")[0]
        actual_message = json.loads(" ".join(message.split(" ")[1:]))

        # cmd.player.name is a 1 integer only if it's sent by the server owner,
        # see servers.py. This is for legacy reasons and how Hotaru was implemented
        # before the rewrite and open-sourcing.
        if message_command == "lock" and cmd.player.name == 1:
            cmd.server.lock = True

        if message_command == "unlock" and cmd.player.name == 1:
            cmd.server.lock = False

        # Send a message.
        if message_command == "chat":
            self.message_send_shorthand(cmd, actual_message)

        # Identical behavior to sending multiple "chat" commands with different contents.
        # Instead, the content is an array of what we would have sent individually
        elif message_command == "chats":
            for ms in actual_message:
                self.message_send_shorthand(cmd, ms)

        # Have you lost a packet? Does your "q" number not match? Fear not, for we have a solution!
        # Call 1-800-REPEAT to receive a copy of all messages that have been sent to you after a specified packet!
        elif message_command == "repeat":
            try:
                cmd.player.client.write_message(json.dumps(
                    {
                        "type": "repeated",
                        "start": actual_message,
                        "repeat": cmd.player.generate_repeat(actual_message)
                    }, ensure_ascii=False))
            except:
                pass