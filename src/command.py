class Command(object):
    def __init__(self):
        self.commands = {
            "hey": self.hey,
            "who let the dogs out?": self.dogs,
            "reese": self.reese,
            "help": self.help
        }

    def handle_command(self, user, command):
        response = "<@" + user + ">: "

        if command in self.commands:
            response += self.commands[command]()
        else:
            response += "Sorry I don't understand the command: " + command + ". " + self.help()

        return response

    def dogs(self):
        return "Who, who, who, who, who"

    def hey(self):
        return "listen!"

    def reese(self):
        return "Oh Reese? Yeah, she's the coolest! Much cooler than my other creator *eyeroll*"

    def help(self):
        response = "Currently I support the following commands:\r\n"

        for command in self.commands:
            response += command + "\r\n"

        return response
