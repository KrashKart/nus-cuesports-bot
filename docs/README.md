---
  layout: default
  title: NUS Cuesports Bot README
  permalink: readme
---

[Home](https://krashkart.github.io/nus-cuesports-bot/)

# NUS Cuesports TeleBot
Repository containing code for the NUS Cuesports TeleBot. This TeleBot is used to manage training polls, notifications and payments.

## TODO
❗Important Changes
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
- [X] Prevent duplication of sessions during confirmation (using Python sets)

📚 Documentation
- [X] Set up Github pages and workflow (Github Actions)
- [X] Index page (landing page)
- [X] Format README.md
- [X] Features page
- [X] Commands page
- [ ] Development page

💡Trivial (optional)
- [X] Change contact details for messages
- [X] Update Google Form link if necessary
- [X] Fix cold start problem (added scheduled ping)
- [X] Add caching system to prevent duplicate messages/callbacks
- [X] Shift code to commands folder and modularize
- [ ] Update help command (command list)
- [ ] Add Google Sheets integration (maybe not?)
- [ ] Clean and refactor code (ongoing...)
