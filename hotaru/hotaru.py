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


class Hotaru(tornado.web.Application):
    """
    Main object for the Tornado server.
    """

    def __init__(self, do_inspect):
        # A reference to this object is passed to all handlers.
        # The ServerPool object holds Server objects, which hold Player objects.
        # This allows to have separate ServerPools on different endpoints,
        # if that is desired.
        self.pool = ServerPool()
        self.html = tornado.template.Loader("./html")

        handlers = [
            ("/ws(.*)", HotaruWebsocket),
            ("/hotaru/(.*)",   HotaruCommands)
        ]

        if do_inspect:
            handlers.append(
                ("/inspect(.*)", HotaruInspector)
            )

        handlers.append(
            ("/(.*)", HotaruLanding)
        )
        super().__init__(handlers)

###          ###
### HANDLERS ###
###          ###


class HotaruLanding(tornado.web.RequestHandler):
    def get(self, input):
        self.write(self.application.html.load("landingpage.html").generate())


class HotaruInspector(tornado.web.RequestHandler):
    """
    Object for the optional Hotaru inspector.
    Currently lacks authentication, but it can be turned off.
    """

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def get(self, cmd):
        logging.debug("Handling request HotaruInspector/" +
                      self.request.path)

        if not cmd.startswith("/"):
            cmd = "/" + cmd
        cmd = cmd.split("/")[1:]

        if cmd[0] == "":
            s = list(self.application.pool.pool.values())
            self.write(self.application.html.load(
                "home.html").generate(a="x", servers=s))

        else:
            serv = self.application.pool.get_server_safe(cmd[0])
            if serv:
                pass  # TODO
            else:
                self.set_status(404)
                self.write("Not found")


class HotaruCommands(tornado.web.RequestHandler):
    """
    Object for the /hotaru endpoint.
    This is where apps ask for new servers, delete them...
    """

    def prepare(self):
        logging.debug("Handling request HotaruCommands/" + self.path_args[0])

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, DELETE')

    def post(self, cmd):
        if cmd.startswith("createServer"):
            limit = int(self.get_argument("limit", -1))
            if limit < 0:
                limit = -1

            prefix = self.get_argument("prefix", "")

            server = self.application.pool.create_server(limit, prefix)
            game_code = server.code
            su = server.su
            logging.info(f"Created new Server: {game_code}")
            self.set_status(201)
            self.write({
                "c": game_code[-4:],
                "su": su
            })
        else:
            self.set_status(404)

    def delete(self, cmd):
        if cmd.startswith("closeServer"):
            server = self.application.pool.get_server_safe(
                self.get_argument("code"))
            if server:
                if server.su == self.get_argument("su"):
                    server.close_server()
                    logging.info(f"Closed server: {server.code}")
                    self.application.pool.free(server.code)
                    self.set_status(200)
                else:
                    self.set_status(401)
            else:
                self.set_status(404)


class HotaruWebsocket(tornado.websocket.WebSocketHandler):
    """
    Main object for the WebSocket endpoint itself.
    This is where actual communication happens.
    """

    def check_origin(self, origin):
        # VERY UNSAFE. This should get a tweak as soon as possible!!!
        return True

    def get_compression_options(self):
        # Non-None enables compression with default options
        return {}

    def xtract_args(self):
        code = self.get_argument("code")
        server = self.application.pool.get_server_safe(code)

        player_name = self.get_argument("name", None)
        player = None
        if server and player_name:
            player = server.get_player_safe(player_name)

        su = self.get_argument("su", None)
        if su and not player_name:
            player = server

        return (server, player_name, player, su)

    def open(self, client):
        logging.debug("Handling request HotaruCommands/" +
                      self.request.path)

        server, player_name, player, su = self.xtract_args()

        # Check for errors in the connection and kick the client if necessary

        if not server:
            self.close(code=exceptions.ServerCodeDoesntExist())
            return

        registering = player_name and not su
        logging_in = player_name and su
        owner_connecting = su and not player_name

        if registering:
            if server.lock:
                self.close(code=exceptions.ServerIsLocked())

            elif server.players.count() == server.limit:
                self.close(code=exceptions.RoomLimitReached())

            elif player:
                self.close(code=exceptions.NameIsTaken())

            elif player_name == "":
                self.close(code=exceptions.NamePropertyIsEmpty())

            else:
                p = Player(player_name, self)
                server.add_user(p)
                su_message = messages.Su(p.su)
                p.write_message(su_message)

                for pb in server.messages_public:
                    p.messages.append(pb)
                    p.next += 1

                append = messages.UserAppend(p)
                server.write_message(append)

        elif logging_in:
            if not player:
                self.close(code=exceptions.NameDoesntExist())

            elif player.su != su:
                self.close(code=exceptions.SuCodeMismatch())

            # The player name exists and the code is correct
            elif player.su == su:
                try:
                    player.client.close(code=exceptions.Overridden())
                except:
                    pass
                player.client = self

                join = messages.UserJoin(player)
                server.write_message(join)

        elif owner_connecting:
            if server.su != su:
                self.close(code=exceptions.SuAdminCodeMismatch())

            # The code checks out
            else:
                try:
                    server.client.close(code=exceptions.Overridden())
                except:
                    pass
                server.client = self

    # We notify the server owner about the disconnection
    def on_connection_close(self):
        if self.close_code:
            if self.close_code != 1000 and self.close_code < 4000:
                server, player_name, player, su = self.xtract_args()
                if server and player:
                    left = messages.UserLeft(player)
                    server.write_message(left)

    # Responsible for delivering messages
    def _send_message(self, server, player, actual_message):
        if actual_message["to"] == 1:
            recipient = server
        elif actual_message["to"] == 2:
            recipient = server.players
        else:
            recipient = server.get_player_safe(actual_message["to"])

        msg = messages.RawMessage(player, actual_message["content"])
        player.sends_message(recipient, msg)

        if actual_message["to"] == 2:
            player.sends_message(server, msg, True)
            server.messages_public.append(msg)

    # Fires when a WS packet is received
    def on_message(self, message, *args):

        # We discard any packet with a length less than or equal to 1.
        # This is for Heroku, it likes to disconnect those that it deems inactive.
        # I usually counter this by sending a whitespace every 5 seconds or so
        if len(message) <= 1:
            return

        server, player_name, player, su = self.xtract_args()

        message_command = message.split(" ")[0]
        actual_message = json.loads(" ".join(message.split(" ")[1:]))

        # player.name is a 1 only if it's sent by the server owner,
        # see servers.py. This is for legacy reasons and how Hotaru was implemented
        # before the rewrite and open-sourcing.
        if message_command == "lock" and player.name == 1:
            server.lock = True

        if message_command == "unlock" and player.name == 1:
            server.lock = False

        # Send a message.
        if message_command == "chat":
            self._send_message(server, player, actual_message)

        # Identical behavior to sending multiple "chat" commands with different contents.
        # Instead, the content is an array of what we would have sent individually
        elif message_command == "chats":
            for ms in actual_message:
                self._send_message(server, player, ms)

        # Have you lost a packet? Does your "q" number not match? Fear not, for we have a solution!
        # Call 1-800-REPEAT to receive a copy of all messages that have been sent to you after a specified packet!
        elif message_command == "repeat":
            try:
                player.client.write_message(json.dumps(
                    {
                        "type": "repeated",
                        "start": actual_message,
                        "repeat": player.generate_repeat(actual_message)
                    }, ensure_ascii=False))
            except:
                pass
