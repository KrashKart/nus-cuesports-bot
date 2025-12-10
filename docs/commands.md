---
  layout: default
  title: NUS Cuesports Bot Commands
  permalink: commands
---

[Home](index.md)

# Commands
- [Legend](#legend)
- [Bot Management](#bot-management)
   * [start](#start)
   * [restart](#restart)
   * [restart_no_save](#restart_no_save)
   * [help](#help)
- [Poll and Confirmation Management](#poll-and-confirmation-management)
   * [prepoll](#prepoll)
   * [poll](#poll)
   * [end_poll](#end_poll)
   * [confirmation](#confirmation)
   * [unconfirm](#unconfirm)
   * [test_prepoll](#test_prepoll)
   * [test_poll](#test_poll)
   * [test_end_poll](#test_end_poll)
- [Scheduling Management](#scheduling-management)
   * [current_schedule](#current_schedule)
   * [update_schedule](#update_schedule)
   * [update_ping](#update_ping)
- [Session Management](#session-management)
   * [view_sessions](#view_sessions)
   * [update_sessions](#update_sessions)
   * [add_session](#add_session)
   * [delete_session](#delete_session)
   * [set_capacity](#set_capacity)
   * [get_paid](#get_paid)
- [Group Management](#group-management)
   * [verify_groups](#verify_groups)
   * [set_admin](#set_admin)
   * [set_recre](#set_recre)
   * [get_group_id](#get_group_id)
- [Super User Management](#super-user-management)
   * [list_super_users](#list_super_users)
   * [is_super_user](#is_super_user)
   * [register_super_user](#register_super_user)
   * [unregister_super_user](#unregister_super_user)
   * [get_user_id](#get_user_id)
- [Miscellaneous](#miscellaneous)
   * [send_admin](#send_admin)
   * [send_recre](#send_recre)

## Legend
* 🛡️ --- Admin group only ([```@_admin_group_perms```](development.md#permissions))
* 👤 --- Super user only ([```@_super_user_perms```](development.md#permissions))

## Bot Management
### start
Usage: ```/start```

Starts the bot.

### restart
🛡️
Usage: ```/restart```

Restarts the bot. Must be called when changing groups/replacing json files so the bot can restart and retrieve the new settings. Even though the bot updates the groups dictionary and json file when changing groups, the ```ADMIN_GROUP``` and ```RECRE_GROUP``` ids are stored as a separate variable, thus are immutable until next restart. ***Saves all jsons in the current state and reloads them upon startup***.

### restart_no_save
🛡️
Usage: ```/restart_no_save```

Restarts the bot, similar to ```restart```. ***Does not save jsons*** and is primarily used for json state modifications without overwriting.

### help
🛡️
Usage: ```/help``` or ```/command_list```

Retrieves the commands list from the bot.

## Poll and Confirmation Management
### prepoll
🛡️
Usage: ```/prepoll```

Manually ends prepoll to the ```RECRE_GROUP```.

### poll
🛡️
Usage: ```/poll```

Manually sends the poll to the ```RECRE_GROUP```. More than one poll can technically exist, polls are managed in a queue.

### end_poll
🛡️
Usage: ```/end_poll```

Manually ends the poll in the ```RECRE_GROUP``` and initiates confirmation. If more than one poll exists, ends the earliest poll established in the group.

### confirmation
🛡️
Usage: ```/confirmation```

Manually sends confirmation information to all polled members, and sends a compilation of those members to the ```ADMIN_GROUP``` for payment tracking.

### unconfirm
🛡️
Usage: ```/unconfirm <user name>```

Unconfirms payment for a user. This command is untested and still a W.I.P.

### test_prepoll
🛡️
Usage: ```/test_prepoll```

Sends an identical prepoll to the ```ADMIN_GROUP```

### test_poll
🛡️
Usage: ```/test_poll```

Sends an identical poll to the ```ADMIN_GROUP```. Beware as this shares the same json file and storage as ```/poll```, so calling this when polls are ongoing in the ```RECRE_GROUP``` ***can overwrite the current data*** from the ongoing polls.

### test_end_poll
🛡️
Usage: ```/test_end_poll```

Ends the test poll in the ```ADMIN_GROUP``` and initiates confirmation.

## Scheduling Management
### current_schedule
🛡️
Usage: ```/current_schedule```

Views the current scheduling datetimes for prepoll, poll and end poll.

### update_schedule
🛡️
Usage: ```/update_schedule <prepoll/poll/end> <day> <time>```

Updates the scheduling for only one of prepoll, poll and end poll. Days must be entered in full and capitals are optional ("Monday" and "monday" are fine) and time must be entered in 24-hour format with a colon (HH:MM).

### update_ping
🛡️
Usage: ```/update_ping <interval in minutes>```

Updates the ping interval, which must be an integer, so the bot will ping at the new interval to prevent cold starts.

## Session Management
Here, we define two types of sessions, active and available. Active sessions are sessions that the bot will include in the poll and prepoll messages, while available sessions are sessions that are stored in the bot but are not sent as an official session.

> ⚠️ IMPORTANT
> Session numbers may change! Sessions are numbered dynamically, so adding or removing sessions may result in different numbering. Always double check!

### view_sessions
🛡️
Usage: ```/view_sessions```

Displays all active and available sessions from the bot as well as their respective capacities, sorted in chronological order with earliest first.

### update_sessions
🛡️
Usage: ```/update_sessions <session 1>...<session 3>```

Choose up to 3 sessions to activate for the week. Select these sessions by including their index number in ***increasing order***. Less than 3 sessions per week is accepted.

### add_session
🛡️
Usage: ```/add_session <day> <start time> <end time>```

Add a new session and declare it *available*. Days must be entered in full and capitals are optional ("Monday" and "monday" are fine) and times must be entered in 24-hour format with a colon (HH:MM).

Also see the [warning about session numbers](#session-management).

### delete_session
🛡️
Usage: ```/delete_session <session number>```

Deletes a session based on the selected session number.

Also see the [warning about session numbers](#session-management).

### set_capacity
🛡️
Usage: ```/set_capacity <session index> <capacity>```

Sets the capacity for the session with the index ```<session index>```.

### get_paid
W.I.P

## Group Management
### verify_groups
🛡️👤
Usage: ```/verify_groups```

Displays group id of the current ```ADMIN_GROUP``` and ```RECRE_GROUP```. Used for debugging and checking if changes to groups are in effect.

### set_admin
👤
Usage: ```/set_admin```

Sets the group this is called in as the ```ADMIN_GROUP```.

Also see the note about changing groups in [```/restart```](#restart).

### set_recre
👤
Usage: ```/set_recre```

Sets the group this is called in as the ```RECRE_GROUP```.

Also see the note about changing groups in [```/restart```](#restart).

### get_group_id
👤
Usage: ```/get_group_id```

Get the group id of the group this is called in.

## Super User Management
### list_super_users
🛡️
Usage: ```/list_super_users```

Displays all super users.

### is_super_user
🛡️
Usage: ```/is_super_user```

Indicates if the user sending the command is a super user.

### register_super_user
🛡️
Usage: ```/register_super_user <nickname>```

Registers the user as a super user under ```<nickname>```.

Nicknames are not checked for duplicates, so do deconflict if necessary.

### unregister_super_user
🛡️
Usage: ```/unregister_super_user```

Unregisters the user as a super user.

### get_user_id
🛡️
Usage: ```/get_user_id```

Get the user id of the user.

## Miscellaneous
### send_admin
🛡️
Usage: ```/send_admin [message]```

Sends a message to ```ADMIN_GROUP``` as the bot. Accepts Telegram's bold, underline and italic formats or HTML formatting.

### send_recre
🛡️
Usage: ```/send_recre [message]```

Sends a message to ```RECRE_GROUP``` as the bot. Accepts Telegram's bold, underline and italic formats or HTML formatting.
