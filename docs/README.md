---
  layout: default
  title: NUS Cuesports Bot README
  permalink: readme
---

[Home](https://krashkart.github.io/nus-cuesports-bot/)

# NUS Cuesports TeleBot
Repository containing code for the NUS Cuesports TeleBot. This TeleBot is used to manage training polls, notifications and payments.

## HOTO
Add new Bot TD to the GCP and share GitHub Repo.

In ```messages.json```,
- Change "Payment Director" and "Bot Director" details
- Update "Confirmation" > "Google Doc" if necessary

In ```config.json```,
- Update super users, add the new Bot TD (in Telegram)

## TODO
Important Changes ❗
- [X] Add super user functionality
  - [X] Register/deregister super user
  - [X] View super users
  - [X] Check if user is super user
  - [X] Add id checking functionality (user id, group id)
- [X] Add session update functionality
  - [X] Update sessions
  - [X] Add/Delete sessions
  - [X] View sessions
  - [X] Segregate active and available sessions
  - [X] Bind session capacity to session itself
- [X] Integrate session capacities functionality
  - [X] Add functionality to change capacities dynamically
  - [X] Enable capacity display in polls
  - [X] Restrict poll confirmation according to session capacity

Bugs 🕷️
- [X] Prevent duplication of sessions during confirmation (using Python sets)
- [X] Fix confirmation pipeline not working properly for test poll functions
- [X] Fix formatting issues in prepoll, poll and confirmation messages

Documentation 📚
- [X] Set up Github pages and workflow (Github Actions)
- [X] Index page (landing page)
- [X] Format README.md
- [X] Features page
- [X] Commands page
- [ ] Development page (temporarily done?)

Trivial 💡
- [X] Add caching system to prevent duplicate messages/callbacks
- [X] Fix cold start problem (added scheduled ping)
  - [X] Add command to change ping interval
- [X] Shift code to commands folder and modularize
- [ ] Enable scheduled ping only during polling periods (difficult)
- [ ] Update help command (temporary fix --- direct to the command links page)
- [X] Clean and refactor code
- [X] Create command permissions
  - [X] Admin group permissions (command can only be used in ADMIN group)
  - [X] Super user permissions (command can only be used by super user)
  - [X] Integrate with all commands
  - [X] Standardize command function parameters for perms wrapper
- [X] Sort payment message by username