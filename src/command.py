from history import get_history, get_link_to_links


class Command(object):
    def __init__(self):
        self.channel = None
        self.commands = {
            "has joined the group": self.history,
            "history": self.history,
            "links": self.links,
            "hey": self.hey,
            "help": self.help
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
        get_history(self.channel)
        return "I've collected the channel's history:\n" + self.links()

    def links(self):
        return get_link_to_links(self.channel)

    def help(self):
        response = "Currently I support the following commands:\r\n"

        for command in self.commands:
            response += command + "\r\n"
        response += "Please see my GitHub for further details:\n <https://github.com/ElBell/Navi-Slackbot/tree/master>"
        return response
