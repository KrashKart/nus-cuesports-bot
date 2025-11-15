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

Other features to note would be:
* [Scheduled Ping](#scheduled-ping)
* [Update ID Caching](#update-id-caching)
* [Permissions Management](#permissions-management)

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
The telebot deals with 4 (types) of groups: ADMIN, RECRE, SPAM TEST and LOGGING.
* ```ADMIN_GROUP``` permits super users to run commands and control bot schedules, sessions, etc.
* ```RECRE_GROUP``` is the official recreational group to send polls to.
* ```SPAM_TEST_GROUP``` is for large-volume testing and aims to reduce spam.
* ```LOGGING_GROUP``` contains logs raised by the bot during operation.

> ⚠️ IMPORTANT
> The SPAM TEST group is already deprecated. Do your testing/logging in the ADMIN or LOGGING group, or create your own group if necessary. DO NOT use ```SPAM_TEST_GROUP```

## Super User Management
Super users are able to set group roles (see [Group Management](#group-management)), which are vital to control command permissions, and view group and user IDs.

Super users can be registered and unregistered in groups where super user operations are permitted. For now, only the ADMIN and SPAM TEST groups allow access to the super user commands.

## Scheduled Ping
To prevent the bot instance from dying, a scheduled ping is run every 10 minutes. This prevents input lag and cold starts, which can severely impact bot response, performance, and even cause duplicate messages due to Telegram's short timeout limit forcing an unnecessary retry.

## Update ID Caching
As a secondary measure to prevent duplicate messages, the bot stores the highest update ID in a "cache". If the next update ID is less than or equal to the highest update ID, it will not process that update.

## Permissions Management
To prevent other users from accessing the bot, a very simple system of two permissions is implemented: Admin Group only, and Super Users only. Using commands when one is not in the ADMIN group and/or is not a super user may lead to the bot rejecting the command.