from command import Command
from history import link_or_attachment, add_link


class Event:
    def __init__(self, bot):
        self.bot = bot
        self.command = Command()

    def wait_for_event(self):
        events = self.bot.slack_client.rtm_read()
        if events and len(events) > 0:
            for event in events:
                # print event
                self.parse_event(event)

    def parse_event(self, event):
        if event and 'text' in event:
            if self.bot.bot_id in event['text']:
                self.handle_event(event['user'], event['text'].split(self.bot.bot_id)[1].strip().lower(), event['channel'])
            elif 'gist.github.com/ElBell' not in event and link_or_attachment(event['text']):
                add_link(event, event['channel'])

    def handle_event(self, user, command, channel):
        if command and channel:
            print("Received command: " + command + " in channel: " + channel + " from user: " + user)
            response = self.command.handle_command(command, channel)
            self.bot.slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True,
                                           unfurl_links=False, unfurl_media=False)
