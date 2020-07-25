from multiprocessing import Pool
from queue import Queue
from functools import partial
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import tkinter.simpledialog
from threading import Thread
from email_conn import *
from parser import *
from database import *
from datetime import datetime

VERSION = '0.0.3'

# Todo: Add way to communicate straight to download interface.

class Application():     
    def __init__(self):
        # Application objects
        self.tasks = []
        self.log = Queue()
        self.bar_log = Queue()
        self.email_app = None # EmailConnection()
        self.email_get = None # EmailGetter()
        self.emails = None # Email list

        self.database = EmailDatabase(self.put_msg, self.add_bar, self.reset_bar)

        # Arrange the basics of window
        self.root = tk.Tk()
        self.root.geometry('1000x750')
        self.root.title('PythonMail Client v.' + VERSION)
        self.root.iconbitmap('favicon.ico')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.style = ttk.Style()
        self.style.configure(
            'Status.TLabel',
            relief=tk.SUNKEN,
            anchor=tk.W,
        )

        self.create_pane()
        # setup email notebook
        self.nEmails = ttk.Notebook(self.root)
        self.nDefault = ttk.Frame(self.nEmails)
        self.nEmails.add(self.nDefault, text='No emails yet: Use search to get some')
        self.nEmails.grid(row=1, column=2, sticky='NSEW')

        # Setup status bar
        self.status = tk.StringVar()
        self.status.set('Not connected')
        self.statuslabel = ttk.Label(
            self.root, textvariable=self.status,
            style='Status.TLabel'
        )
        self.statuslabel.grid(row=2,column=1, sticky='SEW')
        self.progressbar = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=150, mode='determinate', maximum=100)
        self.progressbar.grid(row=2, column=2, sticky='SEW')

        self.create_menu()

        # Configure root grid for even spacing
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=2)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        # Updater
        self.tasks.append(Thread(target=self.update_status))
        self.tasks[-1].setDaemon(True)
        self.tasks[-1].start()
        self.root.mainloop()

    def create_pane(self):
        # Setup paned window
        self.pActions = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        # Setup connection interface
        self.pConnect = ttk.Labelframe(self.pActions, text='Connect', width=200, height=200)
        # Setup download interface
        self.pDownload = ttk.Labelframe(self.pActions, text='Download', width=200, height=200)
        self.pDButton = ttk.Button(self.pDownload, text='Download all email into database', command=self.get_mail_wrapper)
        self.pDButton.pack(fill=tk.X)
        self.pDownloadVal = tk.StringVar()
        self.pDownloadVal.set('Idle')
        self.pDLabel = ttk.Label(self.pDownload, textvariable=self.pDownloadVal)
        self.pDLabel.pack(fill=tk.X)
        # Setup search interface
        self.pSearch = ttk.Labelframe(self.pActions, text='Search', width=200, height=200)
        # Configure paned window
        self.pActions.add(self.pConnect)
        self.pActions.add(self.pDownload)
        self.pActions.add(self.pSearch)
        self.pActions.grid(row=1, column=1, sticky='NSEW')

    def create_menu(self):
        # Setup menu bar
        self.menubar = tk.Menu(self.root)
        self.menubar.add_command(label='Get Mail!', command=self.conv_mail_wrapper)

        # Advanced menu
        self.advmenu = tk.Menu(self.menubar, tearoff=0)
        self.advmenu.add_command(label='Connect', command=self.connect)
        self.advmenu.add_command(label='Download all', command=self.get_mail_wrapper)
        self.advmenu.add_command(label='Save emails in database', command=self.save_mail_wrapper)
        self.advmenu.add_command(label='Load emails in database', command=self.load_mail_wrapper)
        self.advmenu.add_command(label='Reset Database', command=self.database.reset_db)

        # Help Menu
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label='About', command=self.about)

        self.menubar.add_cascade(label='Advanced', menu=self.advmenu)
        self.menubar.add_cascade(label='Help', menu=self.helpmenu)
        self.root.config(menu=self.menubar)

    def close(self):
        for task in self.tasks:
            if task.is_alive():
                self.put_msg('Cannot close, task in progress')
                return False
        self.root.destroy()

    def about(self):
        tk.messagebox.showinfo(
            'About', 
            message='Made by Leo Qi!'
                    '\nVersion: ' + VERSION +
                    '\nConnected to server? ' + str(self.email_app != None) +
                    '\nGot emails?  ' + str(self.email_get != None)
        )
    
    def connect(self):
        if self.email_app == None:
            self.put_msg('Connecting to server...')
            self.email_app = EmailConnection()
            self.put_msg('Connected!')
        else:
            self.log.put('Already connected!')
    
    def get_mail_wrapper(self, threads=None):
        if self.email_app != None:
            if self.email_get == None:
                self.put_msg('Getting messages')
                if threads == None:
                    l_threads = tk.simpledialog.askinteger(
                        'Get messages', 'Enter amount of threads for search (Min 1, Max 10)', 
                        minvalue=1, maxvalue=10
                    )
                    if l_threads == None:
                        self.put_msg('Cancelled.')
                        return False
                else:
                    l_threads = threads

                self.tasks.append(Thread(target=self.get_mail, args=(l_threads,)))
                self.tasks[-1].start()
                return True
            else:
                self.put_msg('Emails already received.')
        else:
            self.put_msg('You must connect to the server first. Connecting...')
            self.connect()
            self.get_mail_wrapper()

    def get_mail(self, threads):
        self.email_get = EmailGetter(self.email_app.conn, threads, self.put_msg, self.add_bar)
        self.email_get.get_emails_online(threads, self.database.get_datestr())
        self.reset_bar()

    def load_mail_wrapper(self):
        self.tasks.append(Thread(target=self._load_mail))
        self.tasks[-1].start()
    
    def _load_mail(self):
        self.emails = self.database.load_emails()

    def save_mail_wrapper(self, emails=None):
        if emails != None:
            self.tasks.append(Thread(target=self.database.save_emails, args=(emails,)))
            self.tasks[-1].start()
        else:
            if self.emails != None:
                self.tasks.append(Thread(target=self.database.save_emails, args=(emails,)))
                self.tasks[-1].start()
            else:
                self.put_msg('No emails to save...')

    def conv_mail_wrapper(self):
        self.tasks.append(Thread(target=self.conv_mail))
        self.tasks[-1].start()

    def conv_mail(self): # convienence class for user
        # Connect
        self.connect()

        # Get mail
        self.get_mail_wrapper(threads=10)
        self.tasks[-1].join()

        self.save_mail_wrapper(self.email_get.emails)
        self.tasks[-1].join()

        self.load_mail_wrapper()
        self.tasks[-1].join()

        self.database.save_last_date(datetime.now())

    def put_msg(self, msg):
        """
        Put a message into the queue to be displayed by the status bar
        Keyword arguments:
        msg -- A string displayed in the status bar
        """
        self.log.put(msg)

    def add_bar(self, amt):
        """
        Add to the progress bar an amount
        Keyword arguments:
        amt -- Amount to add
        """
        self.bar_log.put(amt)

    def reset_bar(self):
        if not self.bar_log.empty():
            while not self.bar_log.empty():
                get = self.bar_log.get()
                self.bar_log.task_done()
        self.progressbar['value'] = 0
        self.root.update_idletasks()

    def update_status(self):
        """
        Refreshes self.root with status of varios infos
        """   
        if not self.log.empty():
            self.status.set(self.log.get())
            self.log.task_done()
        
        if not self.bar_log.empty():
            add_val = self.bar_log.get()
            if self.progressbar['value'] + add_val <= 100:
                self.progressbar['value'] += add_val
            self.bar_log.task_done()
        
        self.root.update_idletasks()
        self.root.after(20, self.update_status)

if __name__ == '__main__':
    app=Application()