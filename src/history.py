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
slack_token = os.environ["OAUTH_ACCESS_TOKEN"]
slack_client = SlackClient(slack_token)


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
    call = "channels.history" if channel_id[0] == "C" else "groups.history"
    while has_more:
        current = slack_client.api_call(call, channel=channel_id, latest=latest)
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


def generate_file(channel_id):
    links = get_links(get_messages(channel_id))
    channel_name = get_channel_name(channel_id)
    links.sort(key=lambda link: link[1], reverse=True)
    file_string = generate_md_file(links, channel_name)
    file = open(f"../files/{channel_name}.md", "w+")
    file.write(file_string)
    file.close()
    return file.name


def get_history(channel_id):
    repo = Repo('/Users/eleonorbart/Projects/Python/Navi')
    commit_message = 'committing links'
    print([generate_file(channel_id)])
    repo.index.add(generate_file(channel_id))
    repo.index.commit(commit_message)
    origin = repo.remote('origin')
    origin.push()


def get_link_to_links(channel_id):
    return f"https://github.com/ElBell/Navi-Slackbot/files/{get_channel_name(channel_id)}.md"


def get_channel_name(channel_id):
    if channel_id[0] == "C":
        return slack_client.api_call("channels.info", channel=channel_id)["channel"]["name"]
    else:
        return slack_client.api_call("groups.info", channel=channel_id)["group"]["name"]
