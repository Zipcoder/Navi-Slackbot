import os
import re
import time
import urllib.request
from datetime import datetime
from typing import List, Dict, Set, Iterator

import requests
from bs4 import BeautifulSoup
from git import Repo
from slackclient import SlackClient

sections = {"github": "GitHub", "stackoverflow": "StackOverflow", "java": "Java", "interview": "Interview", "": "Misc"}
ignored_titles: List[str] = ["not found", "forbidden", "denied"]

slack_token: str = os.environ["OAUTH_ACCESS_TOKEN"]
slack_client: SlackClient = SlackClient(slack_token)


class Link:
    def __init__(self, url, creator, timestamp, reaction_count):
        self.url = url
        self.creator = creator
        self.timestamp = timestamp
        self.reaction_count = reaction_count

    def __key(self):
        return self.url, self.creator, self.timestamp

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(self, type(other)) and self.__key() == other.__key()


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
        current = slack_client.api_call(call, channel=channel_id, latest=latest, count=1000)
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


# get link from message text
def parse_message(message):
    if is_link(message):
        url = message['text'][message['text'].index('<') + 1:message['text'].index('>')]
        return Link(url, message['user'], message['ts'], get_reaction_count(message))


def is_link(message):
    text = message['text']
    if len(text) > 0 and '<' in text and text[text.index('<')+1] == 'h':
        return True


def get_reaction_count(message):
    count = 0
    if "reactions" not in message:
        return count
    for reaction in message["reactions"]:
        count += reaction["count"]


# get links from attachments
def parse_attachments(message):
    attachment_links = []
    for attachment in message['attachments']:
        if 'original_url' in attachment:
            attachment_links.append(Link(attachment['original_url'], message['user'], message['ts'], get_reaction_count(message)))
        if 'app_unfurl_url' in attachment:
            attachment_links.append(Link(attachment['app_unfurl_url'], message['user'], message['ts'], get_reaction_count(message)))
    return attachment_links


def sort_into_sections(links_set: Iterator[Link]):
    sectioned_links = {sections[section]: [] for section in sections.keys()}
    for link in links_set:
        for key, title in sections.items():
            if key in link.url:
                sectioned_links[title].append(link)
    return sectioned_links


def get_links(raw_messages):
    links_set: Set[Link] = set()
    for message in [raw_message for raw_message in raw_messages if 'navi' not in str(raw_message).lower()]:
        if 'attachments' in message:
            links_set.update(parse_attachments(message))
        else:
            links_set.add(parse_message(message))
    return sort_into_sections(filter(None, links_set))


# Getting the possible title from the link using Beautiful Soup
def generate_link_md(link: Link, users):
    try:
        title = BeautifulSoup(requests.get(link.url).text, 'lxml').title.string
        if any(word in title.lower() for word in ignored_titles):
            title = link.url
    except:
        title = link.url
    title = re.sub(r"[\n\t]*", "", title).strip()
    return f"[{title.strip()}]({link.url})<br/>By: {users[link.creator]} " \
        f"Posted: {datetime.fromtimestamp(float(link.timestamp)).strftime('%b %d %Y %I:%M:%S%p')} <br/> "


def generate_md_file(sectioned_links, channel_name):
    users = get_users()
    md_file = [f"# {channel_name}"]
    for title, links in sectioned_links.items():
        md_file.append(f"\n## {title}<br/>\n")
        for link in links:
            md_file.append(generate_link_md(link, users))
    return ''.join(md_file)


def generate_file(channel_id):
    sectioned_links = get_links(get_messages(channel_id))
    channel_name = get_channel_name(channel_id)
    file_string = generate_md_file(sectioned_links, channel_name)
    file = open(f"../files/{channel_name}.md", "w+")
    file.write(file_string)
    file.close()
    return f"files/{channel_name}.md"


def get_history(channel_id):
    repo = Repo('/Users/eleonorbart/Projects/Python/Navi')
    commit_message = 'committing links'
    repo.index.add([generate_file(channel_id)])
    repo.index.commit(commit_message)
    origin = repo.remote('origin')
    origin.push()


def get_link_to_links(channel_id):
    return f"https://github.com/ElBell/Navi-Slackbot/blob/master/files/{get_channel_name(channel_id)}.md"


def get_channel_name(channel_id):
    if channel_id[0] == "C":
        return slack_client.api_call("channels.info", channel=channel_id)["channel"]["name"]
    else:
        return slack_client.api_call("groups.info", channel=channel_id)["group"]["name"]
