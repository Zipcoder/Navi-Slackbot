import os
import re
import time
import json
from datetime import datetime
from typing import List, Dict, Set, Iterator

import requests
from bs4 import BeautifulSoup
from git import Repo
from slackclient import SlackClient

sections = {"git": "GitHub", "stackoverflow": "StackOverflow", "java": "Java", "python": "Python",
            "interview": "Interview", "": "Misc"}
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

    def to_json(self):
        return {
            'url': self.url,
            'creator': self.creator,
            'timestamp': self.timestamp,
            'reaction_count': self.reaction_count
        }

    @classmethod
    def from_json(cls, data):
        return cls(data['url'],
                   data['creator'],
                   data['timestamp'],
                   data['reaction_count'])


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
    message_text = message['text']
    if is_link(message_text):
        url = message_text[message_text.index('<') + 1:message_text.index('>')]
        return [Link(url, message['user'], message['ts'], get_reaction_count(message))]


def is_link(text):
    if len(text) > 0 and '<' in text and text[text.index('<') + 1] == 'h':
        return True
    return False


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
            attachment_links.append(
                Link(attachment['original_url'], message['user'], message['ts'], get_reaction_count(message)))
        if 'app_unfurl_url' in attachment:
            attachment_links.append(
                Link(attachment['app_unfurl_url'], message['user'], message['ts'], get_reaction_count(message)))
    return attachment_links


def sort_into_sections(links_set: Iterator[Link]):
    sectioned_links = {sections[section]: [] for section in sections.keys()}
    for link in links_set:
        sectioned_links[get_section(link)].append(link)
    return sectioned_links


def get_section(link):
    for key, title in sections.items():
        if key in link.url:
            return title


def link_or_attachment(raw_message):
    if 'attachments' in raw_message or is_link(raw_message):
        return True
    return False


def get_links(raw_messages):
    links_set: Set[Link] = set()
    for message in [raw_message for raw_message in raw_messages if 'navi' not in str(raw_message).lower()]:
        links: List[Link] = parse_link_or_attachment(message)
        if links is not None:
            links_set.update(links)
    return sort_into_sections(links_set)


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


def generate_md_file(channel_id, channel_name):
    with open(f"/app/src/files/json/{channel_id}.json") as file_read:
        json_data = json.load(file_read)
    sectioned_links = {category: [Link.from_json(link) for link in links] for category, links in json_data.items()}
    users = get_users()
    md_file = [f"# {channel_name}"]
    for title, links in sectioned_links.items():
        if len(links) > 0:
            md_file.append(f"\n## {title}<br/>\n")
            links.sort(key=lambda x: x.timestamp)
            for link in links:
                md_file.append(generate_link_md(link, users))
    return ''.join(md_file)


def generate_file(channel_id):
    channel_name = get_channel_name(channel_id)
    file_string = generate_md_file(channel_id, channel_name)
    file = open(f"/app/src/files/{channel_name}.md", "w+")
    file.write(file_string)
    file.close()
    return f"src/files/{channel_name}.md"


def original_json(channel_id):
    sectioned_links = get_links(get_messages(channel_id))
    json_data = {category: [link.to_json() for link in links]
                 for category, links in sectioned_links.items()}

    with open(f"/app/src/files/json/{channel_id}.json", 'w') as write_file:
        json.dump(json_data, write_file)
    return f"src/files/json/{channel_id}.json"


def get_history(channel_id):
    original_json(channel_id)
    generate_file(channel_id)

# def push_to_git(file_list):
#     repo = Repo('/app/Navi-Slackbot')
#     commit_message = 'committing links'
#     repo.index.add(file_list)
#     repo.index.commit(commit_message)
#     origin = repo.remote('origin')
#     origin.push()


def get_link_to_links(channel_id):
    return f"https://github.com/ElBell/Navi-Slackbot/blob/master/src/files/{get_channel_name(channel_id)}.md"


def get_channel_name(channel_id):
    if channel_id[0] == "C":
        return slack_client.api_call("channels.info", channel=channel_id)["channel"]["name"]
    else:
        return slack_client.api_call("groups.info", channel=channel_id)["group"]["name"]


def parse_link_or_attachment(message: str) -> List[Link]:
    if 'attachments' in message:
        return parse_attachments(message)
    elif 'text' in message:
        return parse_message(message)


def add_link(message, channel_id):
    links: List[Link] = parse_link_or_attachment(message)
    with open(f"files/json/{channel_id}.json") as file_read:
        json_data = json.load(file_read)
    sectioned_links = {category: [Link.from_json(link) for link in links] for category, links in json_data.items()}
    add_to_section(links, sectioned_links)
    json_data = {category: [link.to_json() for link in links]
                 for category, links in sectioned_links.items()}
    with open(f"/app/src/files/json/{channel_id}.json", 'w') as write_file:
        json.dump(json_data, write_file)
    generate_file(channel_id), f"src/files/json/{channel_id}.json"


def add_to_section(links, sectioned_links):
    for link in links:
        for key, title in sections.items():
            if key in link.url:
                sectioned_links[title].append(link)
    return sectioned_links
