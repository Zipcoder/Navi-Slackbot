from history import get_history, get_link_to_links, get_channel_name, get_link_to_all


class Command(object):
    def __init__(self):
        self.channel = None
        self.commands = {
            "has joined the group": self.history,
            "has joined the channel": self.history,
            "find all": self.find_all,
            "links": self.links,
            "hey": self.hey
        }

    def handle_command(self, command, channel):
        self.channel = channel
        response = ""
        if command in self.commands:
            response += self.commands[command]()
        else:
            response += "Sorry I don't understand the command: " + command + ". " + self.help()

        return response

    def hey(self):
        return "listen!"

    def history(self):
        gist = get_history(self.channel)
        return "I retrieved all the links from " + get_channel_name(self.channel) + ":\n" + gist

    def links(self):
        return get_link_to_links(self.channel)

    def find_all(self):
        return get_link_to_all()

    def help(self):
        response = "Currently I support the following commands:\r\n"
        for command in self.commands:
            if "has joined the" not in command:
                response += command + "\r\n"
        response += "Please see my GitHub for further details:\n https://github.com/ElBell/Navi-Slackbot/tree/master"
        return response
