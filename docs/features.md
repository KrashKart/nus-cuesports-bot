---
  layout: default
  title: NUS Cuesports Bot Features
  permalink: features
---

[Home](index.md)

# Features 📌
The main features are:
* [Poll and Confirmation Automation](#poll-and-confirmation-automation)
* [Scheduler Management](#scheduler-management)
* [Session Management](#session-management)
* [Group Management](#group-management)
* [Super User Management](#super-user-management)
* [Scheduled Ping](#scheduled-ping)

> ℹ️ TIP
> You can view the command format and descriptions in [Commands](commands.md)

## Poll and Confirmation Automation
The telebot will send prepoll, poll, end poll and confirmation messages and update poll headcounts automatically. This is the main functionality of the bot to manage polled members and sessions.

## Scheduler Management
The bot also allows in-house viewing of the scheduled prepoll, poll and end poll functionalities. You can also change the scheduler date and time from the bot itself too.

## Session Management
The telebot also allows handling of the cuesports sessions, allowing temporary changes week by week. 

The bot stores two types of sessions: active, and available. Active sessions are sessions that will be displayed to the RECRE group, but available sessions will not.
However, the bot will still store available sessions that can be declared active at any moment. Likewise, any active session can be deactivated and declared available at any time.

## Group Management
The telebot deals with 4 (types) of groups: ADMIN, RECRE and SPAM TEST.
* The ADMIN group permits super users to run commands and control bot schedules, sessions, etc.
* The RECRE group is the official recreational group to send polls to.
* The SPAM TEST group is for large-volume testing and aims to reduce spam in the ADMIN group.
* The LOGGING group contains logs raised by the bot during operation.

> ⚠️ IMPORTANT
> The SPAM TEST group will be deprecated soon. Do transfer testing/logging to the ADMIN or LOGGING group, or create your own extension if possible.

## Super User Management
Super users are able to set group roles (see [Group Management](#group-management)), which are vital to control command permissions, and view group and user IDs.

Super users can be registered and unregistered in groups where super user operations are permitted. For now, only the ADMIN and SPAM TEST groups allow access to the super user commands.

## Scheduled Ping
To prevent the bot instance from dying, a scheduled ping is run every 10 minutes. This prevents input lag and cold starts, which can severely impact bot response, performance, and even cause duplicate messages due to Telegram's short timeout limit forcing an unnecessary retry.