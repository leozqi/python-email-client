import email.utils
import time
import sys
import os
import pickle
import utils
import sqlite3
import shutil
import stat
from datetime import datetime

class EmailDatabase():
    def __init__(self, print_func=None, bar_func=None, bar_clear=None):
        # Different paths
        self.system_path = sys.path[0]
        self.resource_path = os.path.join(self.system_path, 'resources/')
        if not os.path.exists(self.resource_path):
            os.mkdir(self.resource_path)
        
        self.save_path = os.path.join(self.system_path, 'resources/saved/')
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        self.database_path = os.path.join(self.resource_path, 'manager.db')
        self.data_path = os.path.join(self.resource_path, 'data.pkl')
        # Functions and DB objects
        self.manager = None # sqlite3 db connection
        self.print = print_func
        self.bar = bar_func
        self.bar_clear = bar_clear
        self.load_db()      # loads db
        self.last_date = self._load_last_date()

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
        os.remove(self.data_path)
        shutil.rmtree(self.save_path)
        os.chmod(self.resource_path, stat.S_IWUSR)
        os.mkdir(self.save_path)
        os.chmod(self.save_path, stat.S_IWUSR)
        self.print('Resetted database.')
    
    def save_last_date(self, date):
        """
        Save a datetime.datetime object as a pickle.
        Keyword arguments:
        date - a datetime.datetime object
        """
        with open(self.data_path, 'wb') as out:
            pickle.dump(date, out, pickle.HIGHEST_PROTOCOL)

    def _load_last_date(self):
        """
        Returns the last date of the file.
        Returns: datetime.datetime object or Nonetype if not found.
        """
        try:
            with open(self.data_path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    def get_datestr(self):
        if self.last_date == None:
            return None
        else:
            return self.last_date.strftime('%d-%b-%Y')

    def save_emails(self, email_list):
        """
        Keyword arguments:
        email_list -- The EmailGetter() class's self.emails method, 
                      a list of email tuples of format (message, num)
        """
        if self.manager == None:
            self.print('Loading Database...')
            self.load_db()

        self.print('Saving emails...')
        if len(email_list) == 0:
            self.print('No emails provided.')
            return False
        counter = 1
        email_amt = 100 / len(email_list)
        for email in email_list:
            self.print(f'Saving email {counter}...')
            # Get header values
            subject = email[0].get('Subject')
            date = utils.email_to_datetime(email[0].get('Date'))
            to_line = email[0].get('To')
            from_line = email[0].get('From')

            if (not (isinstance(subject, str) 
                    and isinstance(date, datetime) 
                    and isinstance(to_line, str) 
                    and isinstance(from_line, str))):
                # Check if all inputs are correct
                self.print('Aborting... connection error')
                return False
            
            exists = self.manager.execute(
                'SELECT * FROM emails'
                ' WHERE subject = ? AND created = ?'
                ' AND to_address = ? AND from_address = ?',
                (subject, date, to_line, from_line)
            ).fetchone()

            if exists == None: # only get new emails
                self.manager.execute(
                    'INSERT INTO emails'
                    ' (subject, created, to_address, from_address)'
                    ' VALUES (?, ?, ?, ?)',
                    (subject, date, to_line, from_line),
                )
                self.manager.commit()
                file_id = self.manager.execute(
                    'SELECT last_insert_rowid() FROM emails'
                ).fetchone()
                file_path = os.path.join(
                    self.save_path,
                    "".join( (str(file_id[0]), '.pkl') )
                )
                with open(file_path, 'wb') as out:
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
                file_path = os.path.join(
                    self.save_path,
                    "".join( ( str(ref[0]), '.pkl' ) )
                )
                try:
                    with open(file_path, 'rb') as f:
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
                return None

            self.print('Finished.')
            if self.bar_clear != None:
                self.bar_clear()
            return email_list

        self.print('No emails present.')
        return None

    def tag_emails(self, key_list, tags):
        """
        Tags emails in database
        Keyword arguments:
        email_list -- The EmailGetter() class's self.emails method, 
                      a list of email tuples of format (message, num)
        """
        if self.manager == None:
            self.print('Loading Database...')
            self.load_db()

        self.print('Tagging emails...')
        if len(key_list) == 0:
            self.print('No emails provided.')
            return False
        counter = 1
        key_amt = 100 / len(key_list)

        for key in key_list:
            self.print(f'Tagging email {counter}...')
            self.manager.execute(
                'UPDATE emails SET tags = ?'
                ' WHERE subject = ? AND created = ?'
                ' AND to_address = ? AND from_address = ?',
                (tags, key['Subject'], key['Date'], key['To'], key['From']),
            )
            self.manager.commit()

            counter += 1
            if self.bar != None:
                self.bar(key_amt)

        self.print('Finished')
        if self.bar_clear != None:
            self.bar_clear()
        return True

    def get_tagged_emails(self, tags):
        if self.manager == None:
            self.print('Loading Database...')
            self.load_db()

        self.print('Loading emails...')
        counter = 1
        email_refs = self.manager.execute(
            'SELECT id, tags FROM emails'
        ).fetchall()

        new_tags = tags.split(',')
        if len(email_refs) > 0:
            email_list = []
            for ref in email_refs:
                is_match = False
                if ref['tags'] != None:
                    ref_tags = ref['tags'].split(',')
                    for tag in ref_tags:
                        if tag in new_tags:
                            is_match = True
                            break
                
                if is_match == True:
                    self.print(f'Getting email {counter}...')
                    file_path = os.path.join(
                        self.save_path,
                        "".join( ( str(ref['id']), '.pkl' ) )
                    )
                    with open(file_path, 'rb') as f:
                        email_list.append(pickle.load(f))

                counter += 1
            
            return email_list
        return False