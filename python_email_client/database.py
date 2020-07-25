import email.utils
import time
import sys
import os
import pickle
import utils
import sqlite3
import shutil
import stat

class EmailDatabase():
    def __init__(self, print_func=None, bar_func=None, bar_clear=None):
        self.system_path = sys.path[0]
        self.resource_path = os.path.join(self.system_path, 'resources/')
        self.save_path = os.path.join(self.system_path, 'resources/saved/')
        self.database_path = os.path.join(self.system_path, 'resources/manager.db')
        self.manager = None # sqlite3 db connection
        self.print = print_func
        self.bar = bar_func
        self.bar_clear = bar_clear
        self.load_db()

    def load_db(self):
        if self.manager == None:
            if os.path.exists(self.database_path):
                self.manager = sqlite3.connect(
                    self.database_path,
                    detect_types=sqlite3.PARSE_DECLTYPES,
                    check_same_thread=False
                )
                self.manager.row_factory = sqlite3.Row
            else:
                with open(self.database_path, 'w') as f:
                    pass
                self.load_db()
                with open('schema.sql', 'r') as f:
                    self.manager.executescript(f.read())
        else:
            raise Exception('Database already loaded.')

    def reset_db(self):
        self.print('Resetting...')
        self.manager = None
        os.remove(self.database_path)
        shutil.rmtree(self.save_path)
        os.chmod(self.resource_path, stat.S_IWUSR)
        os.mkdir(self.save_path)
        os.chmod(self.save_path, stat.S_IWUSR)
        self.print('Resetted database.')
    
    def save_emails(self, email_list):
        """
        Keyword arguments:
        email_list -- The EmailGetter() class's self.emails method, 
                      a list of email tuples of format (message, num)
        """
        if self.manager == None:
            self.print('Loading Database...')
            self.load_db()

        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)
        
        self.print('Saving emails...')
        counter = 1
        email_amt = 100 / len(email_list)
        for email in email_list:
            self.print(f'Saving email {counter}...')
            self.manager.execute(
                'INSERT INTO emails (subject, created, to_address, from_address) VALUES (?, ?, ?, ?)',
                (
                    email[0].get('Subject'),
                    utils.email_to_datetime(email[0].get('Date')),
                    email[0].get('To'),
                    email[0].get('From'),
                )
            )
            self.manager.commit()
            file_id = self.manager.execute(
                'SELECT last_insert_rowid() FROM emails'
            ).fetchone()
            with open(os.path.join(self.save_path, "".join(((str(file_id[0])), '.pkl'))), 'wb') as out:
                pickle.dump(email, out, pickle.HIGHEST_PROTOCOL)
            counter += 1
            if self.bar != None:
                self.bar(email_amt)

        self.print('Finished')
        if self.bar_clear != None:
            self.bar_clear()
        return True
    
    def load_emails(self):
        if self.manager == None:
            self.print('Loading Database...')
            self.load_db()

        self.print('Loading emails...')
        counter = 1
        email_refs = self.manager.execute(
            'SELECT id FROM emails'
        ).fetchall()
        email_amt = 100 / len(email_refs)
        if len(email_refs) > 0:
            email_list = []
            directory_corrupt = False
            for ref in email_refs:
                self.print(f'Getting email {counter}...')
                try:
                    with open(os.path.join(self.save_path, "".join((str(ref[0]), '.pkl'))), 'rb') as f:
                        email_list.append(pickle.load(f))
                except FileNotFoundError:
                    directory_corrupt = True
                    break
                counter += 1
                if self.bar != None:
                    self.bar(email_amt)

            if directory_corrupt:
                self.print('Loading database failed... corrupt elements.')
                self.print('Deleting existing database...')
                self.reset_db()
                self.print('Finished.')

                if self.bar_clear != None:
                    self.bar_clear()
                return []

            self.print('Finished.')
            if self.bar_clear != None:
                self.bar_clear()
            return email_list

        self.print('No emails present.')
        return []
