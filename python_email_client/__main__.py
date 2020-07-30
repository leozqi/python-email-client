# -*- coding: utf-8 -*-
#
# -*-----------------*-

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
import utils
from database import *
from email_conn import *
from gui_elements import *

VERSION = utils.get_config()['version']

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

        self.database = EmailDatabase(self.put_msg, self.add_bar,
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
        self.fBottom = tk.Frame(self.root, height=10)
        self.fBottom.pack(side=tk.BOTTOM, fill=tk.X)

        self.pane = OverviewPane(self.fTop, self.search_wrapper, VERSION)
        self.pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrolling_frame = ScrollingFrameAndView(self.fTop)
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

        self.root.config(menu=OverMenu(self.root, self.conv_mail_wrapper,
                                       self.database.reset_db, VERSION))

        # Updater
        self.tasks.append(Thread(target=self.update_status))
        self.tasks[-1].setDaemon(True)
        self.tasks[-1].start()
        self.root.mainloop()
    
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
        '''
        Convienent pre-set method for the Get_Mail
            button, using other defined methods.
        '''
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

        self.pane.set_status(
            f'PythonEmail Client version {VERSION}.'
            '\nEmails loaded and saved.'
            '\nUse the search function to group and view emails')
        self.root.update_idletasks()

    def search_wrapper(self, search_val=None):
        self.pane.disable_search()
        self.root.update_idletasks()
        subject, to_ln, from_ln = self.pane.get_checkboxes()
        search_terms = search_val.replace(' ', '').lower().split(',')
        if len(search_terms) == 0 or search_terms[0] == '':
            tk.messagebox.showerror('Error:', 'No search terms provided.')
            self.pane.enable_search()
            return False
        
        self.pane.set_search_terms(search_terms)
        self.root.update_idletasks()

        if self.emails == None:
            error_msg = (
                'Cannot search: No emails. '
                'Use "Get Emails!" to get emails.')
            tk.messagebox.showwarning(
                'Error',
                message=error_msg
            )
            self.put_msg(error_msg)
            self.pane.enable_search()
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
        self.pane.disable_search()
        self.root.update_idletasks()
        process_message_searches = partial(
            parse_mail.process_message,
            subject=subject,
            to_ln=to_ln,
            from_ln=from_ln,
            search_list=search_terms)
        self.put_msg('Searching messages...')
        count = 0
        yes_count = 0
        no_count = 0
        search_list = []
        self.reset_bar()
        try:
            email_amt = 100 / len(self.emails)
        except ZeroDivisionError:
            email_amt = 0

        with Pool() as pool:
            for i in pool.imap_unordered(process_message_searches, self.emails):
                count += 1
                self.add_bar(email_amt)
                if i != False:
                    search_list.append(i)
                    yes_count += 1
                else:
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
        self.pane.enable_search()
        return False

    def display_mail(self, tags):
        self.scrolling_frame.reset_frame()
        self.root.update_idletasks()
        emails = self.database.get_tagged_emails(tags)
        self.put_msg('Finished getting tagged emails.')
        for email in emails:
            for part in email[0].walk():
                if part.get_content_maintype() == 'text':
                    payload = utils.parse_payload(part.get_payload())
                    if part.get_content_subtype() == 'html':
                        can_view = True
                    else:
                        can_view = False
                    self.scrolling_frame.add_button(
                        utils.parse_sub(email[0].get('Subject')),
                        payload,
                        can_view)
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
        '''
        Refreshes self.root with status of varios infos
        '''
        if not self.log.empty():
            self.status.set(self.log.get())
            self.log.task_done()
        
        if not self.bar_log.empty():
            add_val = self.bar_log.get()
            self.progressbar['value'] += add_val
            self.bar_log.task_done()
        
        active_threads = active_count()
        if self.pane.get_thread_cnt() != active_threads:
            self.pane.set_thread_cnt(active_threads)

        self.root.update_idletasks()
        self.root.after(20, self.update_status)

if __name__ == '__main__':
    app=Application()