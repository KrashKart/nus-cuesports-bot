---
  layout: default
  title: NUS Cuesports Bot Development
  permalink: development
---

[Home](index.md)

# Polling Timeline and Definition
1. First, ***prepoll*** is triggered at Wednesday 1200hrs. The prepoll message format is as listed under ```messages["Prepoll Announcement"]``` under ```messages.json```
1. Next, ***poll*** is triggered at Wednesday 1800hrs. The poll message consists the "questions" (```messages["Poll"]["Question"]```) as the header, "body" (```messages["Poll"]["Body"]```), and the "poll options" (```messages["Poll"]["Options"]```) that contain the name of the sessions (the day and time) and the usernames and handles of the users that polled for the sessions.
1. Then, ***end_poll*** is triggered at Saturday 0000hrs. The poll is disabled (the markup option displays "poll ended") and no further polling requests are accepted.
1. Lastly, ***confirmation*** is triggered immediately after. The bot does the following in order:
  - The bot collates which users are allocated which sessions according to the respective session capacities
  - The bot then tallies sessions by user (that is, it reformats the previous step)
  - The bot calculates how much the user should pay and formats the confirmation message (given in ```messages["Confirmation"]```) which involves the message itself and the link to the Google form (```messages["Confirmation"]["Google Doc"]```)
  - The bot sends the confirmation message to the user, and repeats this process for all other users