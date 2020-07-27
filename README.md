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