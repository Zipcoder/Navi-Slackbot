# Navi-Slackbot
For managing links

Hey! I'm a SlackBot for managing links. When invited to a channel, I go through all past links and collect them into a GitHub .md files. I run on Heroku and keep an ear out for any new links added to a channel. 

I have the following commands:
* "has joined the group"/"has joined the channel" - how I know to go get the history of a new channel I'm invited too. You can also manually enter either command to cause me to go reget the history of a channel. It can take me a while, though, so please only call this if you need to! 
* "find all" - I'll send you a gist that includes links to all the channel gists that I've collected
* "links" - I'll send you a link to that particular channel's gist
* "hey" - listen!
