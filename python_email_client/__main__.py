from multiprocessing import Pool
from queue import Queue
from functools import partial
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import tkinter.simpledialog
from email_conn import *
from parser import *
from database import *
from threading import Thread

VERSION = '0.0.2'

class Application():     
    def __init__(self):
        self.tasks = []
        self.log = Queue()
        # Arrange the basics of window
        self.root = tk.Tk()
        self.root.geometry('1000x750')
        self.root.title('PythonMail Client v.' + VERSION)
        self.root.iconbitmap('favicon.ico')
        #self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.style = ttk.Style()
        self.style.configure(
            'Status.TLabel',
            relief=tk.SUNKEN,
            anchor=tk.W,
        )
        # Setup status bar
        self.status = tk.StringVar()
        self.status.set('Not connected')
        self.statuslabel = ttk.Label(
            self.root, textvariable=self.status,
            style='Status.TLabel'
        )
        self.statuslabel.pack(side=tk.BOTTOM, fill=tk.X)

        # Setup menu bar
        self.menubar = tk.Menu(self.root)
        self.menubar.add_command(
            label='Connect', 
            command=self.connect
        )
        self.menubar.add_command(
            label='Get emails for database', 
            command=self.pre_get_mail
        )
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(
            label='About', 
            command=self.about
        )
        self.menubar.add_cascade(label='Help', menu=self.helpmenu)
        self.root.config(menu=self.menubar)
    
        self.email_app = None # EmailConnection()
        self.email_get = None # EmailGetter()

        # Updater
        self.tasks.append(Thread(target=self.update_status))
        self.tasks[-1].setDaemon(True)
        self.tasks[-1].start()
        self.root.mainloop()
    
    """
    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.root.destroy()
    """

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
    
    def pre_get_mail(self):
        if self.email_app is not None:
            if self.email_get is not None:
                self.put_msg('Getting messages')
                TITLE = 'Get Messages'
                threads = tk.simpledialog.askinteger(
                    TITLE, 'Enter amount of threads for search (Min 1, Max 10)', 
                    minvalue=1, maxvalue=10
                )
                if threads == None:
                    self.put_msg('Cancelled.')
                    return False
            
                self.tasks.append(Thread(target=self.get_mail, args=(threads,)))
                self.tasks[-1].start()
                return True
            else:
                self.put_msg('Emails already received.')
        else:
            self.put_msg('You must connect to the server first. Connecting...')
            self.connect()
            self.pre_refresh()

    def get_mail(self, threads):
        self.email_get = EmailGetter(self.email_app.conn, threads, self.put_msg)

    def put_msg(self, msg):
        """
        Put a message into the queue to be displayed by the status bar

        Keyword arguments:
        msg -- A string displayed in the status bar
        """
        self.log.put(msg)

    def update_status(self):
        """
        Updates the status bar. Do not touch.
        """   
        if not self.log.empty():
            self.status.set(self.log.get())
            self.log.task_done()
        self.root.after(500, self.update_status)

if __name__ == '__main__':
    app=Application()