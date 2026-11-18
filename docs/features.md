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
* [Always-on Instance](#always-on-instance)
* [Update ID Caching](#update-id-caching)
* [Poll State Saving](#poll-state-saving)
* [Permissions Management](#permissions-management)

> ℹ️ TIP
> You can view the command format and descriptions in [Commands](commands.md)

## Poll and Confirmation Automation
The telebot will send prepoll, poll, end poll and confirmation messages and update poll headcounts automatically. This is the main functionality of the bot to manage polled members and sessions.

## Scheduler Management
The bot also allows in-house viewing of the scheduled prepoll, poll and end poll functionalities. You can also change the scheduler date and time from the bot itself too.

## Session Management
The telebot also allows handling of the cuesports sessions, allowing temporary changes week by week. 

The bot stores two types of sessions: active, and available. Active sessions are sessions that will be displayed to ```RECRE_GROUP```, but available sessions will not. However, the bot will still store available sessions that can be declared active at any moment. Likewise, any active session can be deactivated and declared available at any time.

## Group Management
The telebot deals with 4 (types) of groups: ADMIN, RECRE, SPAM TEST and LOGGING.
* ```ADMIN_GROUP``` permits super users to run commands and control bot schedules, sessions, etc.
* ```RECRE_GROUP``` is the official recreational group to send polls to.
* ```SPAM_TEST_GROUP``` is for large-volume testing and aims to reduce spam.
* ```LOGGING_GROUP``` contains logs raised by the bot during operation.

> ⚠️ IMPORTANT
> ```SPAM_TEST_GROUP``` is already deprecated. Do your testing/logging in ```ADMIN_GROUP``` or ```LOGGING_GROUP```, or create your own group if necessary. DO NOT use ```SPAM_TEST_GROUP```.

## Super User Management
Super users are able to set group roles (see [Group Management](#group-management)), which are vital to control command permissions, and view group and user IDs.

Super users can be registered and unregistered in groups where super user operations are permitted. Only ```ADMIN_GROUP``` allows access to the super user commands.

## Always-on Instance
```app.yaml``` sets ```min_instances: 1``` and ```max_instances: 1```, so exactly one instance of the bot is always running. This avoids cold starts (input lag, and duplicate messages from Telegram retrying after a timeout) without needing a scheduled ping like before.

## Update ID Caching
As a secondary measure to prevent duplicate messages, the bot stores the highest update ID in a "cache". If the next update ID is less than or equal to the highest update ID, it will not process that update. To force sequential consistency in messages, the webhook is registered with ```max_connections=1```, so Telegram delivers updates one at a time and in order.

## Poll State Saving
Everything that changes during a poll (votes, payments, which users have started the bot, and the last update ID) is saved together in one file, ```poll_state.json```. To handle bursts of votes, the bot saves this file in the background at most every 2 seconds, and updates the poll message at most every 3 seconds. Voters get an instant "Added to ..." / "Removed from ..." popup, and the poll message catches up a moment later.

## Permissions Management
To prevent other users from accessing the bot, a very simple system of two permissions is implemented: Admin Group only, and super users only. Using commands when one is not in ```ADMIN_GROUP``` and/or is not a super user will lead to the bot rejecting the command.