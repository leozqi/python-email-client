from multiprocessing import Pool
from queue import Queue
from functools import partial
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import tkinter.scrolledtext
from threading import Thread, active_count
from datetime import datetime
import gc

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

        # For Toplevel() dialog
        self.progress_w = None
        self.w_status = None
        self.w_status_lb = None
        self.w_progress_br = None

        self.database = EmailDatabase(self.put_msg, self.add_bar)
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
            anchor=tk.W)
        self.fTop = tk.Frame(self.root)

        self.root.config(menu=OverMenu(self.root, self.conv_mail_wrapper,
                                       self.database.reset_db, VERSION))

        self.pane = OverviewPane(self.fTop, self.search_wrapper, VERSION,
                                 self.show_tags_wrapper, self.show_wrapper,
                                 lambda: self.wrapper(self._conv_mail))
        self.pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrolling_frame = ScrollingFrameAndView(self.fTop)
        self.scrolling_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fTop.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # Tags
        self.tags = []
        database_tags = self.database.load_json()
        if database_tags is not None:
            if 'tags' in database_tags:
                database_tags = database_tags['tags']
                if not database_tags.isspace() and database_tags != '':
                    self.put_tags_wrapper(database_tags)

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
        return True

    def wrapper(self, func, *args):
        '''Wraps the function (func) with args (args) into a thread.
        Allows easy execution without blocking the Tkinter loop
        '''
        if len(args) == 0:
            self.tasks.append(Thread(target=func))
        else:
            self.tasks.append(Thread(target=func, args=args))
        self.tasks[-1].start()

    def _connect(self):
        if self.email_app == None:
            self.put_msg('Connecting to server...')
            self.email_app = EmailConnection()
            if self.email_app.conn is None:
                self.put_msg('Not Connected: Connection error/No internet!')
                tk.messagebox.showerror('Error', 'No internet/Connection error.'
                                                 ' The app was unable to connect'
                                                 ' to the IMAP server.')
            self.put_msg('Connected!')
        else:
            self.log.put('Already connected!')

    def _get_mail(self, threads=None):
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
                self.email_get = EmailGetter(self.email_app.conn, threads,
                                     self.put_msg, self.add_bar)
                self.email_get.get_emails_online(threads, self.database.get_datestr())
                return True
            else:
                self.put_msg('Emails already received.')
        else:
            self.put_msg('You must connect to the server first. Connecting...')
            self.connect()
            self._get_mail()
    
    def _load_mail(self):
        self.emails = self.database.load_emails()

    def _save_mail(self, emails=None):
        if emails is not None:
            self.database.save_emails(emails)
        else:
            self.put_msg('No emails to save...')

    def conv_mail_wrapper(self):
        self.tasks.append(Thread(target=self._conv_mail))
        self.tasks[-1].start()

    def _conv_mail(self): # convienence class for user
        '''Convienent pre-set method for the Get_Mail button
        Uses other defined methods during operation.
        '''
        self._connect()
        self._get_mail(threads=10)
        self._save_mail(self.email_get.emails)
        self.database.save_last_date(datetime.now())
        self.pane.set_status(
            f'PythonEmail Client version {VERSION}.'
            '\nEmails loaded and saved.'
            '\nUse the search function to group and view emails')
        tk.messagebox.showinfo('Info:', 'Finished getting all emails.')

    def show_wrapper(self):
        '''Wraps the display_mail method in a thread for easy access.
        The display_mail method indexes and displayes tagged emails
        from the EmailDatabase() self.database object.
        '''
        self.tasks.append(Thread(target=self.display_mail))
        self.tasks[-1].start()

    def search_wrapper(self, search_val=None):
        '''Wraps the _search function in a thread for easy access'''
        self.tasks.append(Thread(target=self._search,
                          args=(search_val,)))
        self.tasks[-1].start()

    def _search(self, search_val):
        '''
        Performs actual searching function and stores emails in self.searched
        Keyword Arguments:
        search_val -- The search values to search for, in a string:
                      'value1,value2' format
        '''
        self.pane.disable_search()
        self.root.update_idletasks()

        subject, to_ln, from_ln, all_match = self.pane.get_checkboxes()
        search_terms = search_val.replace(' ', '').lower().split(',')
        if len(search_terms) == 0 or search_terms[0] == '':
            tk.messagebox.showerror('Error:', 'No search terms provided.')
            self.pane.enable_search()
            return False
        
        self.pane.set_search_terms(search_terms)
        self._load_mail()
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

        if not all_match and len(search_terms) > 1:
            if not tk.messagebox.askyesno('Warning', ('If multiple tags are'
                                                      ' searched without the'
                                                      ' "All items must match"'
                                                      ' parameter, all the'
                                                      ' results will be tagged'
                                                      ' with every searched tag')):
                self.put_msg('Cancelled.')
                tk.messagebox.showinfo('Info:', 'Cancelled search.')
                self.pane.enable_search()
                return False

        process_message_searches = partial(
            parse_mail.process_message,
            subject=subject,
            to_ln=to_ln,
            from_ln=from_ln,
            search_list=search_terms,
            all_match=all_match)
        self.put_msg('Searching messages...')
        search_list = []
        messages = [ msg[1] for msg in self.emails ]

        try:
            email_amt = 100 / len(messages)
        except ZeroDivisionError:
            email_amt = 0
        
        with Pool() as pool:
            for i in pool.imap_unordered(process_message_searches, messages):
                self.add_bar(email_amt)
                if i != False:
                    search_list.append(i)

        self.put_msg('Finished processing emails.')
        self.searched = search_list
        tags = ','.join(search_terms)
        self.database.tag_emails(search_list, tags)
        self.put_msg('Finished tagging emails.')
        self.display_mail(tags)
        self.pane.enable_search()
        self.pane.set_search_terms('')

    def display_mail(self, tags=None):
        '''Displays mail onto scrolling_frame and updates grouped tags.
        Keyword arguments:
        tags -- the tags provided to update and display. Default is
                None, which gets all emails.
        '''
        self.scrolling_frame.reset_frame()
        self.root.update_idletasks()
        if tags is not None:
            emails = self.database.get_tagged_emails(tags)
        else:
            emails = self.database.get_all_emails()
        
        self.put_msg('Finished getting tagged emails.')

        if not emails or len(emails) == 0:
            tk.messagebox.showinfo('Info', 'No searched emails found')
            return False

        self._display_mail(emails)

        if tags is not None:
            if tk.messagebox.askyesno('Info', 'Found emails: Tag emails? If'
                                              ' emails are not tagged they'
                                              ' must be searched again to'
                                              ' view them.'):
                self.put_tags_wrapper(tags)

        self.scrolling_frame.update_cnt()
        self.put_msg('Finished displaying mail.')
        gc.collect()

    def put_tags_wrapper(self, tags):
        '''Wraps _put_tags with a thread for easy access.'''
        self.tasks.append(Thread(target=self._put_tags, args=(tags,)))
        self.tasks[-1].start()

    def _put_tags(self, tags):
        '''Displays tags (folders) on GUI as well as storing any new
        tags into the database.
        Keyword arguments:
        tags -- a list of tags that can be in any order in lower case.
        '''
        l_tags = [ x for x in tags.split(',') if not x.isspace() and x != '' ]
        if len(l_tags) == 0:
            tk.messagebox.showwarning('Warning',
                                      'Operation aborted, no emails to tag.')
            return False

        bar_amt = 100 / len(l_tags)
        for tag in l_tags:
            if tag not in self.tags:
                self.pane.add_button(tag, tag)
                self.tags.append(tag)
            self.add_bar(bar_amt)

        self.database.store_tags(tags)

    def show_tags_wrapper(self, tags):
        self.tasks.append(Thread(target=self._show_tags, args=(tags,)))
        self.tasks[-1].start()

    def _show_tags(self, tags):
        self.scrolling_frame.reset_frame()
        self.root.update_idletasks()
        emails = self.database.get_tagged_emails(tags)
        if len(emails) == 0:
            return False
        self._display_mail(emails)
        self.scrolling_frame.update_cnt()
        gc.collect()

    def _display_mail(self, emails):
        '''Displays mail by adding buttons to self.scrolling_frame.
        Should never be called on except when used by other methods of
        this class as they handle user input before this step.
        Keyword arguments:
            emails -- list of (email, attached) tuples, where
                      attached is also a list of attached filename paths.
        '''
        payload = None
        can_view = False

        for email, attached in emails:
            for part in email[0].walk():
                if part.get_content_maintype() == 'text':
                    payload = utils.parse_payload(part.get_payload())
                    if part.get_content_subtype() == 'html':
                        can_view = True
                    break

            if attached is not None:
                self.scrolling_frame.add_button(
                    utils.parse_sub(email[0].get('Subject')),
                    payload, can_view, attached)
            else:
                self.scrolling_frame.add_button(
                    utils.parse_sub(email[0].get('Subject')),
                    payload, can_view)

    def put_msg(self, msg):
        '''Put message (msg) into the queue to be shown by status bar'''
        self.log.put(msg)

    def add_bar(self, amt):
        '''Add to the progress bar (amt)'''
        self.bar_log.put(amt)

    def update_status(self):
        '''Refreshes self.root with status of various infos'''
        task_alive = False
        for task in self.tasks: # TODO: make task a tuple of (task_name, actual thread tasks)
            if task.is_alive() and not task.isDaemon():
                task_alive = True
                break
        
        if task_alive:
            if self.progress_w is None:
                self.progress_w = tk.Toplevel()
                self.progress_w.geometry('300x50')
                self.progress_w.title('Task running...')
                self.progress_w.iconbitmap('favicon.ico')
                self.w_status = tk.StringVar()
                self.w_status.set(' ')
                self.w_status_lb = ttk.Label(self.progress_w,
                                             textvariable=self.w_status)
                self.w_progress_br = ttk.Progressbar(self.progress_w,
                                                     orient=tk.HORIZONTAL,
                                                     mode='determinate',
                                                     maximum=100)
                self.w_progress_br['value'] = 0
                self.w_status_lb.pack(fill=tk.X)
                self.w_progress_br.pack(fill=tk.X)
                center(self.progress_w)
            
            set_val = ''
            if not self.log.empty():
                while not self.log.empty():
                    set_val = self.log.get()
                    self.log.task_done()
                self.w_status.set(set_val)

            add_val = 0
            if not self.bar_log.empty():
                while not self.bar_log.empty():
                    add_val += self.bar_log.get()
                    self.bar_log.task_done()
                
                if self.w_progress_br['value'] + add_val > 100:
                    self.w_progress_br['value'] = 100
                else:
                    self.w_progress_br['value'] += add_val

        elif self.progress_w is not None:
            self.w_status_lb.destroy()
            self.w_progress_br.destroy()
            self.progress_w.destroy()
            self.progress_w = None
            self.w_status = None
            self.w_status_lb = None
            self.w_progress_br = None

        active_threads = active_count()
        if self.pane.get_thread_cnt() != active_threads:
            self.pane.set_thread_cnt(active_threads)

        self.root.update_idletasks()
        self.root.after(20, self.update_status)

if __name__ == '__main__':
    app=Application()