---
  layout: default
  title: NUS Cuesports Bot Development
  permalink: development
---

[Home](index.md)

# Development ⚙️
* [Development Cycle](#development-cycle)
* [Permissions](#permissions)
* [Polling Timeline and Definitions](#polling-timeline-and-definition)

## Sites of Interest
* **Buckets** (Cloud Storage > Buckets) --- stores the ```.json``` files the bot reads from
* **Versions** (App Engine > Versions) --- stores deployed instances of the bot
* **Artifact Registry** (Artifact Registry) --- stores the build artifacts from the deployment (can take up a lot of space! Clear this often)
* **Logs Explorer** (Logging > Logs Explorer) --- view your logged stuff here
* **Cloud Scheduler** (Cloud Scheduler) --- control your scheduled tasks here (Important! Start and stop the prepoll/poll/end/ping tasks during on/off-semester periods here)

## Development Cycle
1. First, run ```gcloud app deploy``` and wait for it to upload the deployment.
1. If you need to change the ```.json``` files, head to **Buckets**, then go to the ```recreational-deployment.appspot.com``` bucket for the files.
1. Next, ***test your code***.
1. Afterwards, head to **Versions** and *delete any unwanted instances*.
1. Lastly, go to the **Artifact Registry** and *delete any unwanted artifacts*. These essentially allow GCP to deploy faster (using caches, build files, etc) and are not needed in the long run. You can consider clearing both folders in ```gae-standard``` and both folders in ```asia.gcr.io```.

If you do not do steps 4 and 5, you could incur additional costs for the project, especially if you do not clear the Artifact Registry (like me).

## Permissions
There are 2 main permission wrappers to note when developing commands.
1. First, the ```@_admin_group_perms``` restricts commands to ```ADMIN_GROUP```. If the commands are called outside this group (even if you are a super user), the bot will reject the command.
1. Second, the ```@_super_user_perms``` restricts commands for super users only. All super users can call this ***anywhere***, and the bot will reject all other users *even if they are in ```ADMIN_GROUP```*.

For functions to use either/both of these wrappers, the function ***must take these arguments and these arguments only***: ```bot: TeleBot```, ```message: Message```, ```messages: dict```, ```config: dict```.

There is a third "permission" ```@_log``` to log and report exceptions for functions, but does not actually provide any permission restriction.

## Polling Timeline and Definition
1. First, ***prepoll*** is triggered at Wednesday 1200hrs. The prepoll message format is as listed under ```messages["Prepoll Announcement"]``` under ```messages.json```
1. Next, ***poll*** is triggered at Wednesday 1800hrs. The poll message consists the "questions" (```messages["Poll"]["Question"]```) as the header, "body" (```messages["Poll"]["Body"]```), and the "poll options" (```messages["Poll"]["Options"]```) that contain the name of the sessions (the day and time) and the usernames and handles of the users that polled for the sessions.
1. Then, ***end_poll*** is triggered at Saturday 0000hrs. The poll is disabled (the markup option displays "poll ended") and no further polling requests are accepted.
1. Lastly, ***confirmation*** is triggered immediately after. The bot does the following in order:
  - The bot collates which users are allocated which sessions according to the respective session capacities
  - The bot then tallies sessions by user (that is, it reformats the previous step)
  - The bot calculates how much the user should pay and formats the confirmation message (given in ```messages["Confirmation"]```) which involves the message itself and the link to the Google form (```messages["Confirmation"]["Google Doc"]```)
  - The bot sends the confirmation message to the user, and repeats this process for all other users
