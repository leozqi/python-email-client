Old buttons:

    # connect button
    connectbutton = tk.Button(
        self.root, text='Connect to server',
        command=self.connect)
    connectbutton.pack(side=tk.TOP, fill=tk.X)

    # download button
    downloadmsgs = tk.Button(
        self.root, text='Download Messages',
        command=self.download)
    downloadmsgs.pack(side=tk.TOP, fill=tk.X)

Simpledialog constructors
    tk.simpledialog.askfloat('title', 'prompt')
    tk.simpledialog.askinteger('title', 'prompt')
    tk.simpledialog.askstring('title', 'prompt')

## Distributed Storage

The resources folder will have several files representing each and every email file stored. Each email will be stored in a file for easy access. This data serialization will be done with **CPickle**

An optional additional thing we can do here is to add a search folder inside the resources folder. This folder should contain folders containing the cache of previous searches for easy access.

## Storing load dates

The database will get emails from after the last scan date. If there is no scan date than the database should store all emails. This will lead to a long storage time but will cache all emails. This scan date should be stored in the `loaddate` table of `database.db`, in the resources folder. It should be in the form of a `datetime.datetime` compatible SQLITE3 TIMESTAMP value.

**Load dates should be saved after each get.**

## TODO:
* Have dynamic loading: based on which emails the user requests, load ONLY THOSE from saved files [ ]
* Order sorted emails either descending or ascending from the sqlite3 database. [ ]
    * This order should be changed through a Tkinter button or GUI element.
* Toggle checkbutton for whether or not all search terms should match for an email

Old view file using data URL (failed)

    def view_in_browser(self):
        txt = self.display_txt.get(1.0, tk.END)
        html = urllib.parse.quote(txt, safe='')
        url = 'data:text/html,' + html
        # b = bytes(txt, 'utf-8')
        # url = 'data:text/html;base64,' + base64.b64encode(b).decode('utf-8')
        webbrowser.get(self.config['browser']).open(url)
