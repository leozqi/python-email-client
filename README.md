## Python Email Client:
Python Email Client is an IMAP email client written in 100% Python. It aims to have both reading and sending functionality, with special emphasis on searching and grouping email. Information from read emails aims to be stored client-side, instead of on an email server.

## Documentation

### Distributed Storage

The resources folder will have several files representing each and every email file stored. Each email will be stored in a file for easy access. This data serialization will be done with **CPickle**

An optional additional thing we can do here is to add a search folder inside the resources folder. This folder should contain folders containing the cache of previous searches for easy access.

### Storing load dates

The database will get emails from after the last scan date. If there is no scan date than the database should store all emails. This will lead to a long storage time but will cache all emails. This scan date should be stored in the `loaddate` table of `database.db`, in the resources folder. It should be in the form of a `datetime.datetime` compatible SQLITE3 TIMESTAMP value.

**Load dates should be saved after each get.**

### Storage Database

The storage database (`manager.db`) is intended to replace the `data.json` file storing dates and configuration info. The new table in the database should store profile information in a table called `profiles`. This data should include:

* The profile name, under the `name` field.
* Email under the `email` field.
* Password, under the `password` field.
* Imap Server address, under the `imap` field
* Port, under the `port` field.
* Last date that profile's mailbox was accessed, under the `date` field.
* All tags searched before in the profile, under the `tags` field.

This info should be created for each new profile created by the tkinter program.

### Displaying Emails [Not yet implemented]

Emails should be under "groups" (referred to tags in the code) that mimic folders. Two default folders should be "Read", "Unread", and "All". Clicking any group should bring up all the emails in that group. New groups should be created by a wizard/prompt/button that creates groups based on keywords, email date sent, to/from address, or a combination of these factors.

## Style Guide

* Variables and function names should all have lowercase names with words separated by _ underscores.

## Development Log

**Todo items:**
|TODO|Date|Finished?|
|----|----|---------|
|Have dynamic loading: based on which emails the user requests, load ONLY THOSE from saved files|July 2020| - [ ]|
|Order sorted emails either descending or ascending from the sqlite3 database.|July 2020| - [ ]|
|Toggle checkbutton for whether or not all search terms should match for an email|July 2020| - [x]|
|~~Store datetime.datetime last date stored value AND tag strings together in data.json|July 2020~~|Finished. Discontinued|
|~~Create user profile selection system and store the gathered usernames/passwords/email servers through keyring and the data.json file~~|Aug 8 2020|Discontinued|
|~~Implement GMAIL compatibility with python-oauth2~~|Aug 8 2020|Discontinued.|
|Return a tuple of (id, email) messages by the database instead of just a email|Aug 8 2020| - [x]|
|Allow viewing an email's to email address, from email address, subject line and date sent|Aug 9 2020| - [x]|
|Implement Displaying Email attachments|Aug 11 2020| - [x]|
|Implement Storage Database|Aug 14 2020| - [x]|
|Rewrite gui_elements and `__main__.py` to remove complexity|Aug 15 2020| - [~]|
|Use a profile system to replace the placeholder .env file system to manage email login information|Aug 16 2020| - [x]|

**Bugs:**
|Issue|Date|Fixed?|
|-----|----|------|
|Search values do not show in OverviewPane object|Aug 8 2020| - [x]|
|Certain characters cannot be displayed by TKinter|Aug 8 2020| - [x]|
|Displaying emails from tags lags the application|Aug 9 2020| - [x]|
|Scrollbar is sticky near the top of a window due to the new Scrollbar random scrolling fix|Aug 14 2020| - [x]|