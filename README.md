## Python Email Client:
Python Email Client is an IMAP email client written in 100% Python. It aims to have both reading and sending functionality, with special emphasis on searching and grouping email. Information from read emails aims to be stored client-side, instead of on an email server.

## Documentation

### Distributed Storage

The resources folder will have several files representing each and every email file stored. Each email will be stored in a file for easy access. This data serialization will be done with **CPickle**

An optional additional thing we can do here is to add a search folder inside the resources folder. This folder should contain folders containing the cache of previous searches for easy access.

### Storing load dates

The database will get emails from after the last scan date. If there is no scan date than the database should store all emails. This will lead to a long storage time but will cache all emails. This scan date should be stored in the `loaddate` table of `database.db`, in the resources folder. It should be in the form of a `datetime.datetime` compatible SQLITE3 TIMESTAMP value.

**Load dates should be saved after each get.**

## Style Guide

* Variables and function names should all have lowercase names with words separated by _ underscores.

## Development Log

**Todo items:**
|TODO|Date|Finished?|
|----|----|---------|
|Have dynamic loading: based on which emails the user requests, load ONLY THOSE from saved files|July 2020| - [ ]|
|Order sorted emails either descending or ascending from the sqlite3 database.|July 2020| - [ ]|
|Toggle checkbutton for whether or not all search terms should match for an email|July 2020| - [x]|
|Store datetime.datetime last date stored value AND tag strings together in data.json|July 2020| - [x]|
|Create user selection system and store the gathered usernames/passwords/email servers through keyring and the data.json file|Aug 8 2020| - [ ]|
|Implement GMAIL compatibility with python-oauth2|Aug 8 2020| - [ ]|
|Return a tuple of (id, email) messages by the database instead of just a email|Aug 8 2020| - [x]|

**Bugs:**
|Issue|Date|Fixed?|
|-----|----|------|
|Search values do not show in OverviewPane object|Aug 8 2020| - [x]|
|Certain characters cannot be displayed by TKinter|Aug 8 2020| - [x]|
|Displaying emails lags the application|Aug 9 2020| - [ ]|

### Old snippets!

Old view file using data URL (failed)

    def view_in_browser(self):
        txt = self.display_txt.get(1.0, tk.END)
        html = urllib.parse.quote(txt, safe='')
        url = 'data:text/html,' + html
        # b = bytes(txt, 'utf-8')
        # url = 'data:text/html;base64,' + base64.b64encode(b).decode('utf-8')
        webbrowser.get(self.config['browser']).open(url)
