from hotaru import messages
import uuid
import json


class Player:
    def __init__(self, name: str, client):
        self.name = str(name)
        self.su = str(uuid.uuid4())
        # suclient
        self.client = client
        # msg
        self.messages = []
        self.next = 0

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

    def sends_message(self, to, content, shadowless=False):
        if to.name == 2:
            for recipient in to.list():
                self.sends_message(recipient, content, True)

        if to.name != 2:
            to.write_message(content)

        if not shadowless:
            sh = messages.ShadowOfMessage(to, content)
            self.messages.append(sh)

    def generate_repeat(self, expected_next):
        looped_real_messages = 0
        caret = 0

        for ms in self.messages:
            if looped_real_messages == expected_next:
                break
            if not ms.get("type", "") == "shadow":
                looped_real_messages += 1
            caret += 1

        n = self.messages[caret:]

        return [i.repr() for i in n]
