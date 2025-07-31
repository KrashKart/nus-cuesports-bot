---
  layout: default
  title: NUS Cuesports Bot Commands
  permalink: commands
---

[Home](index.md)

# Commands
- [Bot Management](#bot-management)
   * [start](#start)
   * [restart](#restart)
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
- [Session Management](#session-management)
   * [view_sessions](#view_sessions)
   * [update_sessions](#update_sessions)
   * [add_sessions](#add_sessions)
   * [delete_session](#delete_session)
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

## Bot Management
### start
Usage: ```/start```

Starts the bot.

### restart
Usage: ```/restart```

Restarts the bot. Must be called when changing groups/replacing json files so the bot can restart and retrieve the new settings. Even though the bot updates the groups dictionary and json file when changing groups, the ```ADMIN_GROUP``` and ```RECRE_GROUP``` ids are stored as a separate variable, thus are immutable until next restart.

### help
Usage: ```/help``` or ```/command_list```

Retrieves the commands list from the bot.

## Poll and Confirmation Management
### prepoll
Usage: ```/prepoll```

Manually ends prepoll to the ```RECRE_GROUP```.

### poll
Usage: ```/poll```

Manually sends the poll to the ```RECRE_GROUP```. More than one poll can technically exist, polls are managed in a queue.

### end_poll
Usage: ```/end_poll```

Manually ends the poll in the ```RECRE_GROUP```. If more than one poll exists, ends the earliest poll established in the group. Note that unlike the automated ```end_poll```, confirmation is not automated here.

### confirmation
Usage: ```/confirmation```

Manually sends confirmation information to all polled members, and sends a compilation of those members to the ```ADMIN_GROUP``` for payment tracking. This command is still a W.I.P.

### unconfirm
Usage: ```/unconfirm <user name>```

Unconfirms payment for a user. This command is untested and still a W.I.P.

### test_prepoll
Usage: ```/test_prepoll```

Sends an identical prepoll to the ```ADMIN_GROUP```

### test_poll
Usage: ```/test_poll```

Sends an identical poll to the ```ADMIN_GROUP```. Beware as this shares the same json file and storage as ```/poll```, so calling this when polls are ongoing in the ```RECRE_GROUP``` ***can overwrite the current data*** from the ongoing polls.

### test_end_poll
Usage: ```/test_end_poll``

Ends the test poll in the ```ADMIN_GROUP```. Does not start confirmation like ```/end_poll```.

## Scheduling Management
### current_schedule
Usage: ```/current_schedule```

Views the current scheduling datetimes for prepoll, poll and end poll.

### update_schedule
Usage: ```/update_schedule <prepoll/poll/end> <day> <time>```

Updates the scheduling for only one of prepoll, poll and end poll. Days must be entered in full and capitals are optional ("Monday" and "monday" are fine) and time must be entered in 24-hour format with a colon (HH:MM).

## Session Management
Here, we define two types of sessions, active and available. Active sessions are sessions that the bot will include in the poll and prepoll messages, while available sessions are sessions that are stored in the bot but are not sent as an official session.

> ⚠️ IMPORTANT
> Session numbers may change! Sessions are numbered dynamically, so adding or removing sessions may result in different numbering. Always double check!

### view_sessions
Usage: ```/view_sessions```

Displays all active and available sessions from the bot, sorted in chronological order with earliest first.

### update_sessions
Usage: ```/update_sessions <session 1>...<session 3>```

Choose up to 3 sessions to activate for the week. Select these sessions by including their index number in ***increasing order***. Less than 3 sessions per week is accepted.

### add_sessions
Usage: ```/add_session <day> <start time> <end time>```

Add a new session and declare it *available*. Days must be entered in full and capitals are optional ("Monday" and "monday" are fine) and times must be entered in 24-hour format with a colon (HH:MM).

Also see the [warning about session numbers](#session-management).

### delete_session
Usage: ```/delete_session <session number>```

Deletes a session based on the selected session number.

Also see the [warning about session numbers](#session-management).

## Group Management
### verify_groups
Usage: ```/verify_groups```

Displays group id of the current ```ADMIN_GROUP``` and ```RECRE_GROUP```. Used for debugging and checking if changes to groups are in effect.

### set_admin
Usage: ```/set_admin```

Sets the group this is called in as the ```ADMIN_GROUP```. ***Only super users can call this***.

Also see the note about changing groups in [```/restart```](#restart).

### set_recre
Usage: ```/set_recre```

Sets the group this is called in as the ```RECRE_GROUP```. ***Only super users can call this***.

Also see the note about changing groups in [```/restart```](#restart).

### get_group_id
Usage: ```/get_group_id```

Get the group id of the group this is called in. ***Only super users can call this***.

## Super User Management
### list_super_users
Usage: ```/list_super_users```

Displays all super users. ***This can only be called in the ```ADMIN_GROUP```.***

### is_super_user
Usage: ```/is_super_user```

Indicates if the user sending the command is a super user. ***This can only be called in the ```ADMIN_GROUP```.***

### register_super_user
Usage: ```/register_super_user <nickname>```

Registers the user as a super user under ```<nickname>```. ***This can only be called in the ```ADMIN_GROUP```.***

Nicknames are not checked for duplicates, so do deconflict if necessary.

### unregister_super_user
Usage: ```/unregister_super_user```

Unregisters the user as a super user. ***This can only be called in the ```ADMIN_GROUP```.***
