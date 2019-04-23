import os
from slackclient import SlackClient
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from git import Repo


slack_token = os.environ["SLACK_API_TOKEN"]
sc = SlackClient(slack_token)

# Get channels
raw_channels = sc.api_call(
    "channels.list"
)['channels']
unarchived_large_channels = [channel for channel in raw_channels if not channel['is_archived'] and len(channel['members']) > 5]
channels = {}
for channel in unarchived_large_channels:
    channels[channel['id']] = channel['name']

print(channels)
# Get users
raw_users = sc.api_call(
    "users.list"
)
users = {}
for user in raw_users['members']:
    if 'profile' in user:
        users[user['id']] = user['profile']['real_name']


# Get messages
def get_messages(channel_id):
    return sc.api_call(
        "channels.history",
        channel=channel_id
    )['messages']


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
    links = set()
    for message in raw_messages:
        print(message)
        parse_message(message, links)
        if 'attachments' in message:
            for attachment in message['attachments']:
                parse_attachment(attachment, message, links)
    return links


repo = Repo('/Users/eleonorbart/Projects/Python/Navi')
commit_message = 'Trial committing file'
fileList = []
for channel_id in channels.keys():
    links = get_links(get_messages(channel_id))
    if len(links) > 0:
        #file = open(f"navi/files/{channels[channel_id]}.md", "w+")
        #file.write(f"# {channels[channel_id]} \n\n")
        for link in links:
            try:
                title = BeautifulSoup(requests.get(link[0]).text, 'lxml').title.string
            except:
                title = link
           # file.write(f"[{title}]({link[0]})\n\nBy: {users[link[2]]}"
                      # f" Posted: {datetime.fromtimestamp(float(link[1])).strftime('%b %d %Y %I:%M:%S%p')}\n\n")
       # file.close()
       # fileList.append(file.name)
# repo.index.add(fileList)
# repo.index.commit(commit_message)
# origin = repo.remote('origin')
# origin.push()
