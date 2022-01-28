class JoinLimiter:
    def __init__(self):
        self.strikes = 0
        self.striking_test = 0

        self.banned_until = 0


class RoomJoinLimiting:
    def __init__(self):
        self.ips = {
            "0.0.0.0": JoinLimiter()
        }

    def get_ratelimit_data(self, ip):
        if not ip in self.ips:
            self.ips[ip] = JoinLimiter()
        return self.ips[ip]


class RoomCreateLimiting:
    def __init__(self):
        self.owns = {

        }

    def check_ip_owns(self, ip):
        return self.owns.get(ip, 0)

    def ip_own(self, ip):
        self.owns[ip] = self.owns.get(ip, 0) + 1

    def ip_deown(self, ip):
        self.owns[ip] = self.owns.get(ip, 0) - 1
        if self.owns[ip] <= 0:
            self.owns.pop(ip)
