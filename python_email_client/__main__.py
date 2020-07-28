from multiprocessing import Pool
from queue import Queue
from functools import partial
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import tkinter.simpledialog
import tkinter.scrolledtext
from threading import Thread, active_count
from datetime import datetime

# Custom modules:
import parse_mail
from database import *
from email_conn import *
from scrolling_frame import *

VERSION = '0.0.4'
class Application():     
    def __init__(self):
        # Application objects
        self.tasks = []
        self.log = Queue()
        self.bar_log = Queue()
        self.email_app = None   # EmailConnection()
        self.email_get = None   # EmailGetter()
        self.emails = None      # Email list
        self.searched = None    # Searched list

        self.database = EmailDatabase(self.put_msg,
                                      self.add_bar,
                                      self.reset_bar)

        # Arrange the basics of window
        self.root = tk.Tk()
        self.root.geometry('1000x750')
        self.root.title(''.join( ('PythonMail Client v.', VERSION) ))
        self.root.iconbitmap('favicon.ico')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.style = ttk.Style()
        self.style.configure(
            'Status.TLabel',
            relief=tk.SUNKEN,
            anchor=tk.W,
        )
        self.fTop = tk.Frame(self.root)
        self.fTop.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fLeft = tk.Frame(self.fTop)
        self.fLeft.pack(side=tk.LEFT, fill=tk.BOTH)
        self.fBottom = tk.Frame(self.root, height=10)
        self.fBottom.pack(side=tk.BOTTOM, fill=tk.X)

        self.create_pane()
        self.scrolling_frame = ScrollingFrameAndView(self.fLeft)
        self.scrolling_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        # Setup status bar
        self.status = tk.StringVar()
        self.status.set('Not connected')
        self.statuslabel = ttk.Label(
            self.fBottom, textvariable=self.status,
            style='Status.TLabel',
        )
        self.statuslabel.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progressbar = ttk.Progressbar(self.fBottom, orient=tk.HORIZONTAL,
                                           length=150, mode='determinate',
                                           maximum=100)
        self.progressbar.pack(side=tk.LEFT)

        self.create_menu()

        # Updater
        self.tasks.append(Thread(target=self.update_status))
        self.tasks[-1].setDaemon(True)
        self.tasks[-1].start()
        self.root.mainloop()

    def create_pane(self):
        # Setup paned window
        self.pActions = ttk.Panedwindow(self.fLeft, orient=tk.VERTICAL)

        # Setup interface
        self.pOverview = ttk.Labelframe(self.pActions, text='Overview')
        self.pOLabelVal = tk.StringVar()
        self.pOLabelVal.set(
            f'PythonEmail Client version {VERSION}.'
            '\nNo emails loaded.'
            '\nPress the "Get Emails" button to get emails.'
        )
        self.pOLabel = ttk.Label(self.pOverview, textvariable=self.pOLabelVal)
        self.pOLabel.pack(fill=tk.X)

        self.pOThreadNum = tk.StringVar()
        self.pOThreadNum.set(str(active_count()))
        self.pOThreadLabel = ttk.Label(self.pOverview,
                                       textvariable=self.pOThreadNum)
        self.pOThreadLabel.pack(fill=tk.X)

        # Setup search interface
        self.pSearch = ttk.Labelframe(self.pActions, text='Search')
        self.pSLabel = ttk.Label(self.pSearch,
                                 text='Enter comma separated tag '
                                      'values to search for:')
        self.pSLabel.pack(fill=tk.X)
        self.pSEntry = ttk.Entry(self.pSearch)
        self.pSEntry.pack(fill=tk.X)
        self.pSButton = ttk.Button(self.pSearch, text='Search!',
                                   command=self.search_wrapper)
        self.pSButton.pack(fill=tk.X)

        # Checkbuttons
        self.search_subject = tk.IntVar()
        self.search_to = tk.IntVar()
        self.search_from = tk.IntVar()
        self.pSSearchSub = tk.Checkbutton(self.pSearch,
                                          text='Search subject lines?',
                                          variable=self.search_subject,
                                          onvalue=1, offvalue=0)
        self.pSSearchSub.pack()
        self.pSSearchTo = tk.Checkbutton(self.pSearch,
                                         text='Search "to" lines?',
                                         variable=self.search_to,
                                         onvalue=1, offvalue=0)
        self.pSSearchTo.pack()
        self.pSSearchFrom = tk.Checkbutton(self.pSearch,
                                           text='Search "from" lines?',
                                           variable=self.search_from,
                                           onvalue=1, offvalue=0)
        self.pSSearchFrom.pack()

        # Feedback
        self.pSLabelVal = tk.StringVar()
        self.pSLabelVal.set(' ')
        self.pSLabel = ttk.Label(self.pSearch, textvariable=self.pSLabelVal)
        self.pSLabel.pack(fill=tk.X)

        # Configure paned window
        self.pActions.add(self.pOverview)
        self.pActions.add(self.pSearch)
        self.pActions.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def create_menu(self):
        # Setup menu bar
        self.menubar = tk.Menu(self.root)
        self.menubar.add_command(label='Get Mail!', 
                                 command=self.conv_mail_wrapper)

        # Advanced menu
        self.advmenu = tk.Menu(self.menubar, tearoff=0)
        self.advmenu.add_command(label='Connect', command=self.connect)
        self.advmenu.add_command(label='Download all',
                                 command=self._get_mail_wrapper)
        self.advmenu.add_command(label='Save emails in database',
                                 command=self.save_mail_wrapper)
        self.advmenu.add_command(label='Load emails in database',
                                 command=self.load_mail_wrapper)
        self.advmenu.add_command(label='Reset Database',
                                 command=self.database.reset_db)

        # Help Menu
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label='About', command=self.about)

        self.menubar.add_cascade(label='Advanced', menu=self.advmenu)
        self.menubar.add_cascade(label='Help', menu=self.helpmenu)
        self.root.config(menu=self.menubar)

    # def _frame_configure(self, event):
    #     self.display_port.configure(scrollregion=self.display_port.bbox('all'))
    
    def close(self):
        for task in self.tasks:
            if task.is_alive():
                error_msg = 'Cannot close, task in progress.'
                self.put_msg(error_msg)
                tk.messagebox.showwarning(
                    'Error',
                    message=error_msg)
                return False
        self.root.destroy()

    def about(self):
        tk.messagebox.showinfo(
            'About', 
            message='Made by Leo Qi!'
                    '\nVersion: ' + VERSION)

    def connect(self):
        if self.email_app == None:
            self.put_msg('Connecting to server...')
            self.email_app = EmailConnection()
            self.put_msg('Connected!')
        else:
            self.log.put('Already connected!')

    def _get_mail_wrapper(self, threads=None):
        if self.email_app != None:
            if self.email_get == None:
                self.put_msg('Getting messages')
                if threads == None:
                    l_threads = tk.simpledialog.askinteger(
                        'Get messages',
                        'Enter amount of threads for search (Min 1, Max 10)',
                        minvalue=1, maxvalue=10
                    )
                    if l_threads == None:
                        self.put_msg('Cancelled.')
                        return False
                else:
                    l_threads = threads

                self.tasks.append(Thread(target=self.get_mail,
                                  args=(l_threads,)))
                self.tasks[-1].start()
                return True
            else:
                self.put_msg('Emails already received.')
        else:
            self.put_msg('You must connect to the server first. Connecting...')
            self.connect()
            self._get_mail_wrapper()

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
            self.tasks.append(
                Thread(target=self.database.save_emails, args=(emails,))
            )
            self.tasks[-1].start()
        else:
            if self.emails != None:
                self.tasks.append(
                    Thread(target=self.database.save_emails, args=(emails,))
                )
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
        self._get_mail_wrapper(threads=10)
        self.tasks[-1].join()

        self.save_mail_wrapper(self.email_get.emails)
        self.tasks[-1].join()

        self.load_mail_wrapper()
        self.tasks[-1].join()

        self.database.save_last_date(datetime.now())

        self.pOLabelVal.set(
            f'PythonEmail Client version {VERSION}.'
            '\nEmails loaded and saved.'
            '\nUse the search function to group and view emails')
        self.root.update_idletasks()

    def search_wrapper(self):
        self.root.update_idletasks()
        subject = self.search_subject.get()
        to_ln = self.search_to.get()
        from_ln = self.search_from.get()
        search_terms = self.pSEntry.get().replace(' ', '').lower().split(',')
        string = ''
        for search in search_terms:
            string = "".join((string, search, '\n'))
        
        self.pSLabelVal.set(string)
        self.root.update_idletasks()

        if self.emails == None:
            error_msg = (
                'Cannot search: No emails.'
                'Use "Get Emails!" to get emails.')
            tk.messagebox.showwarning(
                'Error',
                message=error_msg
            )
            self.put_msg(error_msg)
            self.pSEntry.delete(0, tk.END)
            return False

        self.tasks.append(Thread(target=self._search,
                          args=(subject, to_ln, from_ln, search_terms)))
        self.tasks[-1].start()

    def _search(self, subject, to_ln, from_ln, search_terms):
        """
        Performs actual searching function and stores emails in self.searched
        Keyword Arguments:
        subject -- Boolean value of whether to search in subject line
        to_ln -- Boolean value of whether to search in to line
        from_ln -- Boolean value of whether to search in from line
        search_terms -- A list of possible search terms.
        """
        if self.emails == None:
            self.put_msg('No emails to search through')
            return False

        process_message_searches = partial(
            parse_mail.process_message,
            subject=subject,
            to_ln=to_ln,
            from_ln=from_ln,
            search_list=search_terms)
        self.put_msg('Searching messages -> ')
        count = 0
        yes_count = 0
        no_count = 0
        search_list = []
        with Pool() as pool:
            for i in pool.imap_unordered(process_message_searches, self.emails):
                count += 1
                if i != False:
                    search_list.append(i)
                    self.put_msg(f'Message {count} match')
                    yes_count += 1
                else:
                    self.put_msg(f'Message {count} did not match')
                    no_count += 1
        percent = 0
        try:
            percent = (yes_count/no_count) * 100
        except ZeroDivisionError:
            percent = 0

        self.put_msg('Finished processing emails.')
        self.put_msg(f'Processed {count} messages.')
        self.put_msg(f'{percent}% ({yes_count}/{yes_count + no_count}) of messages match')
        self.searched = search_list
        tags = ','.join(search_terms)
        self.database.tag_emails(search_list, tags)
        self.put_msg('Finished tagging emails.')
        self.display_mail(tags)
        return False

    def display_mail(self, tags):
        emails = self.database.get_tagged_emails(tags)
        self.put_msg('Finished getting tagged emails.')
        for email in emails:
            for part in email[0].walk():
                if part.get_content_maintype() == 'text':
                    self.scrolling_frame.add_button(email[0].get('Subject'),
                                                    part.get_payload())
                    break
    
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
            #if self.progressbar['value'] + add_val <= 100:
            self.progressbar['value'] += add_val
            self.bar_log.task_done()
        
        if int(self.pOThreadNum.get()) != active_count():
            self.pOThreadNum.set(active_count())

        self.root.update_idletasks()
        self.root.after(10, self.update_status)

if __name__ == '__main__':
    app=Application()