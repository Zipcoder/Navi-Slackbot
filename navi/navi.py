import os
import re
import time
import urllib.request
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from git import Repo
from slackclient import SlackClient

sections = {"GitHub": "github"}
slack_token = os.environ["SLACK_API_TOKEN"]
slack_client = SlackClient(slack_token)


# Get channels only if not archived and with more than 5 members
def get_channels():
    raw_channels = slack_client.api_call(
        "channels.list"
    )['channels']
    unarchived_large_channels = [channel for channel in raw_channels
                                 if not channel['is_archived'] and len(channel['members']) > 5]
    channels = {}
    for channel in unarchived_large_channels:
        channels[channel['id']] = channel['name']
    return channels


# Get users for mapping onto their ids
def get_users():
    raw_users = slack_client.api_call("users.list")
    users = {}
    for user in raw_users['members']:
        if 'profile' in user:
            users[user['id']] = user['profile']['real_name']
    return users


# Get messages
def get_messages(channel_id):
    all_messages = []
    has_more = True
    latest = datetime.now().timestamp()
    while has_more:
        current = slack_client.api_call("channels.history", channel=channel_id, latest=latest)
        if not current['ok'] and current['error'] == 'ratelimited':
            time.sleep(int(current['headers']['Retry-After']))
        else:
            try:
                all_messages += current['messages']
                has_more = current['has_more']
                latest = all_messages[len(all_messages) - 1]['ts']
            except:
                print(current)
    return all_messages


# get links from message text
def parse_message(message, links):
    if len(message['text']) > 0 and '<' in message['text']:
        potential_link = message['text'][message['text'].index('<') + 1:message['text'].index('>')]
        if potential_link[0] != '@' and potential_link[0] != '!':
            links.add((potential_link, message['ts'], message['user']))


# get links from attachments
def parse_attachment(attachment, message, links):
    if 'original_url' in attachment:
        links.add((attachment['original_url'], message['ts'], message['user']))
    if 'app_unfurl_url' in attachment:
        links.add((attachment['app_unfurl_url'], message['ts'], message['user']))


def get_links(raw_messages):
    links_set = set()
    for message in raw_messages:
        parse_message(message, links_set)
        if 'attachments' in message:
            for attachment in message['attachments']:
                parse_attachment(attachment, message, links_set)
    return list(links_set)


# Getting the possible title from the link using Beautiful Soup
def generate_link_md(link):
    try:
        title = BeautifulSoup(requests.get(link[0]).text, 'lxml').title.string
        if "site not found" in title:
            title = link[0]
    except:
        title = link[0]
    users = get_users()
    return f"[{title.strip()}]({link[0]})<br/>By: {users[link[2]]} " \
        f"Posted: {datetime.fromtimestamp(float(link[1])).strftime('%b %d %Y %I:%M:%S%p')}<br/>"


# Figure out where to put file link based on section
def get_insertion_index(link, md_file):
    for section in sections.keys():
        if sections[section] in link[0].lower():
            return md_file.index(f"\n## {section}<br/>\n") + 1
    return md_file.index(f"\n## Misc<br/>\n") + 1


def generate_md_file(links, channel_name):
    md_file = [f"# {channel_name}"]
    for section in sections.keys():
        md_file.append(f"\n## {section}<br/>\n")
    md_file.append("\n## Misc<br/>\n")
    for link in links:
        md_file.insert(get_insertion_index(link, md_file), generate_link_md(link))
    return ''.join(md_file)


def generate_file_list():
    file_list = []
    channels = get_channels()
    for channel_id in channels.keys():
        links = get_links(get_messages(channel_id))
        if len(links) > 0:
            links.sort(key=lambda link: link[1], reverse=True)
            file_string = generate_md_file(links, channels[channel_id])
            file = open(f"navi/files/{channels[channel_id]}.md", "w+")
            file.write(file_string)
            file.close()
            file_list.append(file.name)
    return file_list


def get_history():
    repo = Repo('/Users/eleonorbart/Projects/Python/Navi')
    commit_message = 'committing links'
    repo.index.add(generate_file_list())
    repo.index.commit(commit_message)
    origin = repo.remote('origin')
    origin.push()


#
# # starterbot's user ID in Slack: value is assigned after the bot starts up
# navi_id = None
#
# # constants
RTM_READ_DELAY = 1  # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "hi!"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

#
# def parse_bot_commands(slack_events):
#     """
#         Parses a list of events coming from the Slack RTM API to find bot commands.
#         If a bot command is found, this function returns a tuple of command and channel.
#         If its not found, then this function returns None, None.
#     """
#     for event in slack_events:
#         if event["type"] == "message" and not "subtype" in event:
#             user_id, message = parse_direct_mention(event["text"])
#             if user_id == starterbot_id:
#                 return message, event["channel"]
#     return None, None
#
#
# def parse_direct_mention(message_text):
#     """
#         Finds a direct mention (a mention that is at the beginning) in message text
#         and returns the user ID which was mentioned. If there is no direct mention, returns None
#     """
#     matches = re.search(MENTION_REGEX, message_text)
#     # the first group contains the username, the second group contains the remaining message
#     return (matches.group(1), matches.group(2).strip()) if matches else (None, None)
#
#
# def handle_command(command, channel):
#     """
#         Executes bot command if the command is known
#     """
#     # Default response is help text for the user
#     default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)
#
#     # Finds and executes the given command, filling in response
#     response = None
#     # This is where you start to implement more commands!
#     if command.startswith(EXAMPLE_COMMAND):
#         response = "Sure...write some more code then I can do that!"
#
#     # Sends the response back to the channel
#     slack_client.api_call(
#         "chat.postMessage",
#         channel=channel,
#         text=response or default_response
#     )
#
#
# if __name__ == "__main__":
#     if slack_client.rtm_connect(with_team_state=False):
#         print("Starter Bot connected and running!")
#         # Read bot's user ID by calling Web API method `auth.test`
#         starterbot_id = slack_client.api_call("auth.test")["user_id"]
#         while True:
#             command, channel = parse_bot_commands(slack_client.rtm_read())
#             if command:
#                 handle_command(command, channel)
#             time.sleep(RTM_READ_DELAY)
#     else:
#         print("Connection failed. Exception traceback printed above.")

if __name__ == "__main__":
    if slack_client.rtm_connect():
        print("Successfully connected, listening for events")
        while True:
            read = slack_client.rtm_read()
            if len(read) > 0:
                print(read)
            time.sleep(1)
    else:
        print(slack_client.api_call('rtm.connect'))
