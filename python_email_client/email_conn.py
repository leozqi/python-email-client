from email import message_from_bytes
from imaplib import IMAP4_SSL
from queue import Queue, Empty
from threading import Thread, Lock
import utils
import tkinter as tk
import socket
import gc

class LoginError():
    def __init__(self, error_msg=''):
        self.error_msg = error_msg

class EmailConnection():
    def __init__(self, config, print_func=None):
        '''Defines an email connection to our IMAP server.
        Requires a valid dotenv file to be present.
        Be sure to delete the object afterwards to log out of the server.

        Keyword arguments
        config -- a dictionary containing configuration values:
            * config['email'] is the email address of profile
            * config['pswrd'] is the email account's password.
            * config['imap'] is the email account's imap server.
            * config['port'] is the email imap server's port (eg. 993)
        print_func -- An Application() class's put_msg function
        '''
        try:
            self.email = config['email']
            self.pswrd = config['password']
            self.imap = config['imap']
            self.port = config['port']
        except KeyError:
            raise ValueError('Improper configuration passed to EmailConnection')

        try:
            self.conn = IMAP4_SSL(self.imap, self.port)
            try:
                self.conn.login(self.email, self.pswrd)
            except:
                self.conn = LoginError()
        except socket.gaierror:
            self.conn = None

        self.print = print_func

    def __del__(self):
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn.logout()
            except:
                self.conn = None
## End class EmailConnection ##

class EmailGetter:
    def __init__(self, conn, threads, config, print_func, bar_func=None):
        """
        Keyword arguments:
        conn -- An EmailConnection connection (EmailConnection.conn)
        threads -- An integer representing the amount of threads to spawn
        print_func -- An Application() class's put_msg function
        bar_func -- An Application() class's add_bar function
        """
        self.active = True
        self.conn = conn
        self.message_queue = Queue()
        self.finished_queue = Queue()
        self.get_lock = Lock()
        self.workers = []
        self.print = print_func
        self.bar = bar_func
        self.emails = None
        self.config = config

    def __del__(self):
        self.active = False

    def get_emails_online(self, threads, since):
        self.print('Creating threads...')
        msg_amt = int(self.conn.select('INBOX')[1][0].decode('utf-8'))
        self.print(
            'There are '
            + str(msg_amt)
            + ' messages in INBOX'
        )
        msg_bar = 100 / msg_amt
        
        self.conn.select('INBOX')

        # Search code
        last_date = since
        search_str = ''
        if last_date == None:
            search_str = 'ALL'
        else:
            search_str = f'(SINCE "{last_date}")'
        typ, messages = self.conn.search(None, search_str)
        self.print('Searching messages...')
        if typ == 'OK' and messages[0]:
            self.active = True
            self.print('Got list of messages!')
            self.print('Downloading messages...')
            for index, num in enumerate(messages[0].split()):
                self.message_queue.put(num)

            for x in range(threads):
                self.workers.append(Thread(target=self.fetch, args=(msg_bar,)))
                self.workers[-1].start()

            self.message_queue.join()
            self.print('Finished!')
            self.print('Shutting down threads...')
            self.active = False
            self.print('Threads finished.')
            self.print('Sorting messages... ')
            msg_list = list(self.finished_queue.queue)
            self.print('Finished sorting messages!')

            self.emails = msg_list
            print(self.emails)
            return True
        else:
            self.print('No message response...')
            self.emails = []
            return False

    def fetch(self, inc_amt):
        '''A worker function that logs in and retrieves emails from a source.
        Keyword arguments:
        inc_amt -- the amount that progress bar should 
                   increment for message proccessed.
        '''
        email = EmailConnection(self.config)
        conn = email.conn
        try:
            conn.select('INBOX')
        except:
            return False
        
        while self.active:
            if not self.message_queue.empty():
                self.get_lock.acquire()
                try:
                    msg_num = self.message_queue.get(timeout=2)
                except Empty:
                    return True
                self.get_lock.release()
                display_msg_num = msg_num.decode('utf-8')
                status, data = conn.fetch(msg_num, '(RFC822)')
                message = message_from_bytes(data[0][1])
                self.finished_queue.put((message, msg_num))
                self.message_queue.task_done()
                self.print(f'Got message {display_msg_num}')
                if self.bar != None:
                    self.bar(inc_amt)
        return True

    def get_subjects(self, num_list):
        subject_list = []
        for item in self.emails:
            if item[1] in num_list:
                subject_list.append(item[0].get('Subject'))
        return subject_list

    def reset(self):
        self.active = False
        self.emails = None
        with self.message_queue.mutex:
            self.message_queue.queue.clear()
        
        with self.finished_queue.mutex:
            self.finished_queue.queue.clear()

        self.workers = []
## End EmailGetter class ##