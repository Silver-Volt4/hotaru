from hotaru import messages
import uuid
import json

import logging

"""
Class for handling connected players.
"""


class Player:
    def __init__(self, name: str, client):
        self.name = str(name)
        self.su = str(uuid.uuid4())
        self.client = client
        self.messages = []
        self.next = 0

    # This is used when something sends a message TO this player
    def write_message(self, message):
        try:
            self.client.write_message(json.dumps(
                {
                    "type": "inbound",
                    "q": self.next,
                    "msg": message.repr()
                }
            ))
        except:
            pass

        self.next += 1
        self.messages.append(message)

    # This is used when THIS PLAYER sends something to someone else
    def sends_message(self, to, content, shadowless=False):
        # This is how we identify that we're dealing with a PlayerPool object
        if to.name == 2:
            for recipient in to.list():
                # Run this function again, but one message by one.
                # Pass True so that we don't get millions of undesired shadows,
                # but instead get one that was sent to "2"
                self.sends_message(recipient, content, True)

        # When we're dealing with anyone but a PlayerPool
        if to.name != 2:
            to.write_message(content)

        # Write down a shadow so that we include a copy of this sent message
        # when the player asks for a log
        if not shadowless:
            sh = messages.ShadowOfMessage(to, content)
            self.messages.append(sh)

    # This is what generates a repeat, or in other words, a log of everything sent
    # from and to this player. It's used for packet losses, reconnecting, and so on
    def generate_repeat(self, expected_next):
        logging.debug(
            f"Generating repeat packet for {self.name}; Next expected packet is {expected_next}")
        looped_real_messages = 0
        caret = 0

        # Clients should only keep the number of messages they have received.
        # We loop through all messages that this object holds, and count those
        # that have been sent from someone else to this user.

        # This might get changed, because it could cause shadow message duplication in some cases

        for ms in self.messages:
            if looped_real_messages == expected_next:
                break
            if not ms.get("type", "") == "shadow":
                looped_real_messages += 1
            caret += 1

        n = self.messages[caret:]

        return [i.repr() for i in n]
