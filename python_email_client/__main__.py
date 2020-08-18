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
import time

# Custom modules:
import parse_mail
import utils
from database import *
from email_conn import *
from gui_elements import *

import infos

class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
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

        self.database = EmailDatabase(self.wait_window, self.put_msg,
                                      self.add_bar)

        # Arrange the basics of window
        self.geometry('1000x750')
        self.title(''.join( ('PythonMail Client v.', infos.VERSION) ))
        self.iconbitmap('favicon.ico')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.style = ttk.Style()
        self.style.configure(
            'Status.TLabel',
            relief=tk.SUNKEN,
            anchor=tk.W)
        self.config(menu=OverMenu(self, self.database.reset_db))

        # Left paned window \
        self.left_pw = ttk.Panedwindow(self, orient=tk.VERTICAL)

        # Overview -\
        self.view_lf = ttk.Labelframe(self.left_pw, text='Overview')
        self.view_sv = tk.StringVar()
        self.view_sv.set(
            f'PythonEmail Client version {infos.VERSION}.'
            '\nPress the "Get Emails" button to get emails.')
        self.view_lb = ttk.Label(self.view_lf,
                                 textvariable=self.view_sv)
        self.view_lb.pack(fill=tk.X)
        self.view_thnum = tk.StringVar()
        self.view_thnum.set('1')
        self.view_thlb = ttk.Label(self.view_lf,
                                   textvariable=self.view_thnum)
        self.view_thlb.pack(fill=tk.X)
        self.view_rfbt = ttk.Button(self.view_lf,
                                    text='Sync with server',
                                    command=lambda: self.wrapper(
                                        self._conv_mail))
        self.view_rfbt.pack(fill=tk.X)
        self.view_shbt = ttk.Button(self.view_lf, text='Show All Emails',
                                    command=lambda: self.wrapper(
                                        self.display_mail))
        self.view_shbt.pack(fill=tk.X)
        self.view_upbt = ttk.Button(self.view_lf, text='Edit profile',
                                    command=self.database.edit_profile)
        self.view_upbt.pack(fill=tk.X)
        self.view_chbt = ttk.Button(self.view_lf, text='Change profile',
                                    command=self.database.configure_profile)
        self.view_chbt.pack(fill=tk.X)

        # Search -\
        self.search_lf = ttk.Labelframe(self.left_pw, text='Search')
        self.search_lb = ttk.Label(self.search_lf,
                                   text='Enter comma separated search'
                                        ' values to search for:')
        self.search_lb.pack(fill=tk.X)
        self.search_en = ttk.Entry(self.search_lf)
        self.search_en.pack(fill=tk.X)
        self.search_bt = ttk.Button(self.search_lf, text='Search!',
                                    command= lambda: self.wrapper(
                                        self._search, self.search_en.get()))
        self.search_bt.pack(fill=tk.X)

        self.search_sub = tk.IntVar()
        self.search_to = tk.IntVar()
        self.search_from = tk.IntVar()
        self.search_all = tk.IntVar()
        self.search_sub_ch = tk.Checkbutton(self.search_lf,
                                            text='Search subject lines?',
                                            variable=self.search_sub,
                                            onvalue=1, offvalue=0)
        self.search_sub_ch.pack()
        self.search_to_ch = tk.Checkbutton(self.search_lf,
                                           text='Search "to" lines?',
                                           variable=self.search_to,
                                           onvalue=1, offvalue=0)
        self.search_to_ch.pack()
        self.search_from_ch = tk.Checkbutton(self.search_lf,
                                             text='Search "from" lines?',
                                             variable=self.search_from,
                                             onvalue=1, offvalue=0)
        self.search_from_ch.pack()
        self.search_all_ch = tk.Checkbutton(self.search_lf,
                                         text='All terms must match?',
                                         variable=self.search_all,
                                         onvalue=1, offvalue=0)
        self.search_all_ch.pack()

        self.search_fd_lb = ttk.Label(self.search_lf, text='Search values')
        self.search_fd_lb.pack(fill=tk.X)
        self.search_terms = tk.StringVar()
        self.search_terms.set(' ')
        self.search_terms_lb = ttk.Label(self.search_lf,
                                         textvariable=self.search_terms)
        self.search_terms_lb.pack(fill=tk.X)

        # Tag functions -\
        self.previous_lf = ttk.Labelframe(self.left_pw, text='Grouped Tags')
        self.prev_searches = ScrollFrame(self.previous_lf)
        self.prev_searches.pack(fill=tk.BOTH, expand=True)

        # Configure paned window
        self.left_pw.add(self.view_lf)
        self.left_pw.add(self.search_lf)
        self.left_pw.add(self.previous_lf)
        self.left_pw.pack(side=tk.LEFT, fill=tk.BOTH)

        # Scrolling Frame \
        self.scrolling_frame = ScrollingFrameAndView(self)
        self.scrolling_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tags \
        self.database.configure_profile()
        self.tags = []
        profile_info = self.database.load_profile_info()
        if profile_info['tags'] is not None:
            database_tags = profile_info['tags']
            if not utils.is_whitespace(database_tags):
                self.put_tags_wrapper(database_tags)

        # Updater \
        self.tasks.append(Thread(target=self.update_status))
        self.tasks[-1].daemon = True
        self.tasks[-1].start()

    def close(self):
        '''Closes the window. Checks before if any tasks are alive.'''
        for task in self.tasks:
            if task.is_alive() and not task.isDaemon():
                error_msg = 'Cannot close, task in progress.'
                self.put_msg(error_msg)
                tk.messagebox.showwarning('Error', message=error_msg)
                return False
        self.destroy()
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
            if self.database.p_id is None:
                tk.messagebox.showwarning('Warning', 'Please select a profile'
                                                     ' before connecting to an'
                                                     ' email server.')
                return False
            self.email_app = EmailConnection(self.database.load_profile_info())
            if self.email_app.conn is None:
                self.put_msg('Not Connected: Connection error/No internet!')
                tk.messagebox.showerror('Error', 'No internet/Connection error.'
                                                 ' The app was unable to connect'
                                                 ' to the IMAP server.')
                return False
            if isinstance(self.email_app.conn, LoginError):
                self.put_msg('Login error. Check your profile\'s login info.')
                tk.messagebox.showerror('Error', 'Login error. Check your'
                                                 ' profile\'s login'
                                                 ' information.')
                return False

            self.put_msg('Connected!')
            return True
        else:
            self.put_msg('Already connected!')

    def _get_mail(self, threads=None):
        if self.email_app is not None:
            if self.email_get is not None:
                self.email_get.reset()

            self.put_msg('Getting messages')
            if threads is None:
                l_threads = tk.simpledialog.askinteger('Get messages',
                                                        'Enter amount of'
                                                        ' threads for search'
                                                        ' (Min 1, Max 10)',
                                                        minvalue=1, maxvalue=10)
                if l_threads is None:
                    self.put_msg('Cancelled.')
                    return False
            else:
                l_threads = threads
            self.email_get = EmailGetter(self.email_app.conn, threads,
                                            self.database.load_profile_info(),
                                            self.put_msg, self.add_bar)
            self.email_get.get_emails_online(threads, self.database.get_datestr())
            return True
        else:
            self.put_msg('You must connect to the server first. Connecting...')
            self._connect()
            self._get_mail()
    
    def _load_mail(self):
        self.emails = self.database.load_emails()

    def _save_mail(self, emails=None):
        if emails is not None:
            return self.database.save_emails(emails)
        elif self.email_get is not None:
            if self.email_get.emails is not None:
                return self.database.save_emails(self.email_get.emails)

    def _conv_mail(self):
        '''Convienent pre-set method for the Get_Mail button
        Uses other defined methods during operation.
        '''
        connect_success = self._connect()
        if not connect_success:
            tk.messagebox.showerror('Error', 'Connection to server failed...')
            return False
        self._get_mail(threads=10)
        save_success = self._save_mail(self.email_get.emails)
        if not save_success:
            tk.messagebox.showinfo('Info', 'No new emails to save')
        self.database.save_date_now()
        self.view_sv.set(
            f'PythonEmail Client version {infos.VERSION}.'
            '\nEmails loaded and saved.'
            '\nUse the search function to group and view emails')
        tk.messagebox.showinfo('Info:', 'Finished getting all emails.')
        gc.collect()

    def _search(self, search_val):
        '''
        Performs actual searching function and stores emails in self.searched
        Keyword Arguments:
        search_val -- The search values to search for, in a string:
                      'value1,value2' format
        '''
        self.disable_search()
        self.update_idletasks()

        subject, to_ln, from_ln, all_match = self.get_checkboxes()
        search_terms = search_val.replace(' ', '').lower().split(',')
        if len(search_terms) == 0 or search_terms[0] == '':
            tk.messagebox.showerror('Error:', 'No search terms provided.')
            self.enable_search()
            return False
        
        self.set_search_terms(search_terms)
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
            self.enable_search()
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
                self.enable_search()
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
        self.enable_search()
        self.set_search_terms('')

    def display_mail(self, tags=None):
        '''Displays mail onto scrolling_frame and updates grouped tags.
        Wraps on top of self._display_mail
        Keyword arguments:
        tags -- the tags provided to update and display. Default is
                None, which gets all emails.
        '''
        self.scrolling_frame.reset_frame()
        self.update_idletasks()
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
        l_tags = utils.make_tag_list(tags)
        if len(l_tags) == 0:
            tk.messagebox.showwarning('Warning',
                                      'Operation aborted, no emails to tag.')
            return False

        bar_amt = 100 / len(l_tags)
        for tag in l_tags:
            if tag not in self.tags:
                self.prev_searches.add_button(tag, self._show_tags, tag)
            self.add_bar(bar_amt)

        self.database.store_tags(tags)

    def _show_tags(self, tags):
        self.scrolling_frame.reset_frame()
        self.update_idletasks()
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

            email_info = {
                'Subject:': utils.parse_complete_sub(email[0].get('Subject')),
                'Date sent:': email[0].get('Date'),
                'To:': utils.parse_complete_sub(email[0].get('To')),
                'From:': utils.parse_complete_sub(email[0].get('From'))}

            if attached is not None:
                self.scrolling_frame.add_button(
                    utils.parse_sub(email[0].get('Subject')),
                    payload, can_view, attached, email_info)
            else:
                self.scrolling_frame.add_button(
                    utils.parse_sub(email[0].get('Subject')),
                    payload, can_view, None, email_info)

    def put_msg(self, msg):
        '''Put message (msg) into the queue to be shown by status bar'''
        self.log.put(msg)

    def add_bar(self, amt):
        '''Add to the progress bar (amt)'''
        self.bar_log.put(amt)

    def update_status(self):
        while True:
            '''Refreshes self with status of various infos'''
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
            if self.get_thread_cnt() != active_threads:
                self.view_thnum.set(str(active_threads))

            self.update_idletasks()
            time.sleep(0.02)

    # PanedWindow
    def set_search_terms(self, searches):
        string = ''
        for search in searches:
            string = "".join((string, search, '\n'))
        self.search_terms.set(string)

    def get_checkboxes(self):
        return (self.search_sub.get(), self.search_to.get(),
                self.search_from.get(), self.search_all.get())

    def get_thread_cnt(self):
        return int(self.view_thnum.get())

    def clear_entry(self):
        self.search_en.delete(0, tk.END)

    def enable_search(self):
        self.search_bt.configure(state=tk.NORMAL)

    def disable_search(self):
        self.search_bt.configure(state=tk.DISABLED)

if __name__ == '__main__':
    app=Application()
    app.mainloop()