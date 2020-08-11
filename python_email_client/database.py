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
import json
import tkinter as tk
import tkinter.messagebox

class EmailDatabase():
    def __init__(self, print_func=None, bar_func=None, bar_clear=None):
        '''
        Initializes an email database.
        Keyword arguments:
            print_func -- a method outputting information to a window
            bar_func -- a method that adds an amount to a ttk.progressBar
            bar_clear -- a method that clears the progress bar.
        '''
        # Different paths
        self.system_path = sys.path[0]
        self.resource_path = os.path.join(self.system_path, 'resources/')
        if not os.path.exists(self.resource_path):
            os.mkdir(self.resource_path)

        self.save_path = os.path.join(self.system_path, 'resources/saved/')
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        self.attach_path = os.path.join(self.system_path, 'resources/attach/')
        if not os.path.exists(self.attach_path):
            os.mkdir(self.attach_path)

        self.database_path = os.path.join(self.resource_path, 'manager.db')
        self.json_path = os.path.join(self.resource_path, 'data.json')

        # Functions and DB objects
        self.manager = self._load_db() # sqlite3 db connection

        # If any functions not provided, default all to standard print func.
        if print_func == bar_func == bar_clear == None:
            self.print = print
            self.bar = print
            self.bar_clear = print
        else:
            self.print = print_func
            self.bar = bar_func
            self.bar_clear = bar_clear

        self.last_date = self._load_last_date()

    def _load_db(self):
        '''
        Returns a stored SQLITE3 database. Creates one if one is not found.
        The path of the database is stored at the self.database_path attribute.
        '''
        if os.path.exists(self.database_path):
            db = sqlite3.connect(
                self.database_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False
            )
            db.row_factory = sqlite3.Row
            return db
        else:
            with open(self.database_path, 'x') as f:
                pass
            db = self._load_db()
            with open('schema.sql', 'r') as f:
                db.executescript(f.read())
            db.commit()
            return db

    def reset_db(self):
        '''Resets the database. Deletes all database contents.'''
        self.print('Resetting...')
        self.manager = None
        os.remove(self.database_path)
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        shutil.rmtree(self.save_path)
        os.chmod(self.resource_path, stat.S_IWUSR)
        os.mkdir(self.save_path)
        os.chmod(self.save_path, stat.S_IWUSR)
        shutil.rmtree(self.attach_path)
        os.mkdir(self.attach_path)
        os.chmod(self.attach_path, stat.S_IWUSR)

        if os.path.exists(os.path.join(self.resource_path, 'temp/data.html')):
            os.remove(os.path.join(self.resource_path, 'temp/data.html'))
        self.print('Resetted database.')

    def save_last_date(self, date):
        '''
        Save a datetime.datetime object as a string POSIX timestamp.
        Keyword arguments:
        date - a datetime.datetime object
        '''
        stored = datetime.timestamp(date)
        if not os.path.exists(self.json_path):
            data = {
                'date': stored
            }
            with open(self.json_path, 'w') as f:
                json.dump(data, f)
            return True

        data = self.load_json()
        if data is None:
            data = {}
            data['date'] = stored

        with open(self.json_path, 'w') as f:
            json.dump(data, f)

    def _load_last_date(self):
        '''
        Returns the last date that the email server was accessed.
        Returns: datetime.datetime object or Nonetype if not found.
        '''
        try:
            with open(self.json_path, 'r') as f:
                data = self.load_json()
                if data is None:
                    return None
                elif 'date' not in data:
                    return None
                else:
                    return datetime.fromtimestamp(data['date'])
        except FileNotFoundError:
            return None

    def get_datestr(self): 
        if self.last_date == None:
            return None
        else:
            return self.last_date.strftime('%d-%b-%Y')

    def save_emails(self, email_list):
        '''
        Keyword arguments:
        email_list -- The EmailGetter() class's self.emails method, 
                      a list of email tuples of format (message, num)
        '''
        self.print('Saving emails...')
        if len(email_list) == 0:
            self.print('No new emails to save.')
            return False

        email_amt = 100 / len(email_list)
        for email in email_list:
            # Get header values
            subject = email[0].get('Subject')
            if subject is None:
                subject = 'No subject provided...'
            date = utils.email_to_datetime(email[0].get('Date'))
            to_line = email[0].get('To')
            from_line = email[0].get('From')

            if (not (isinstance(subject, str)
                    and isinstance(date, datetime)
                    and isinstance(to_line, str)
                    and isinstance(from_line, str))):
                # Check if all inputs are correct
                tk.messagebox.showerror('Error', 'Aborting... connection error. Resetting.')
                self.print('Aborting... connection error. Resetting.')
                self.reset_db()
                return False
            
            exists = self.manager.execute(
                'SELECT * FROM emails'
                ' WHERE subject = ? AND created = ?'
                ' AND to_address = ? AND from_address = ?',
                (subject, date, to_line, from_line)
            ).fetchone()

            if exists is None: # only get new emails
                self.manager.execute(
                    'INSERT INTO emails'
                    ' (subject, created, to_address, from_address, read)'
                    ' VALUES (?, ?, ?, ?, ?)',
                    (subject, date, to_line, from_line, 0),
                )
                self.manager.commit()
                mail_id = self.manager.execute(
                    'SELECT last_insert_rowid() FROM emails'
                ).fetchone()
                mail_path = os.path.join(
                    self.save_path,
                    "".join( (str(mail_id[0]), '.pkl') )
                )
                with open(mail_path, 'wb') as out:
                    pickle.dump(email, out, pickle.HIGHEST_PROTOCOL)

                # Also save potential attachments
                for part in email[0].walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if not part.get('Content-Disposition'):
                        continue

                    if part.get_filename() is None:
                        continue
                    elif part.get_filename().isspace() or part.get_filename() == '':
                        continue

                    filename, file_ext = os.path.splitext(part.get_filename())
                    self.manager.execute(
                        'INSERT INTO files (filename, extension, email_lk)'
                        ' VALUES (?, ?, ?)',
                        (filename, file_ext, mail_id[0]),
                    )
                    self.manager.commit()
                    
                    file_id = self.manager.execute(
                        'SELECT last_insert_rowid() FROM files'
                    ).fetchone()
                    file_path = os.path.join(
                        self.attach_path,
                        ''.join( (str(file_id[0]), file_ext) )
                    )
                    with open(file_path, 'wb') as out:
                        out.write(part.get_payload(decode=1))

            if self.bar != None:
                self.bar(email_amt)

        self.print('Finished')
        if self.bar_clear != None:
            self.bar_clear()
        return True
    
    def load_emails(self):
        '''Returns a tuple of (id, email_msg) values.'''
        self.print('Loading emails...')
        counter = 1
        email_refs = self.manager.execute(
            'SELECT id FROM emails'
        ).fetchall()

        if len(email_refs) > 0:
            email_amt = 100 / len(email_refs)
            email_list = []
            directory_corrupt = False
            for ref in email_refs:
                mail_path = os.path.join(
                    self.save_path,
                    "".join( ( str(ref[0]), '.pkl' ) ))
                try:
                    with open(mail_path, 'rb') as f:
                        email_list.append( (ref[0], pickle.load(f)) )
                except FileNotFoundError:
                    directory_corrupt = True
                    break
                counter += 1
                if self.bar != None:
                    self.bar(email_amt)

            if directory_corrupt:
                self.print('Loading database failed... corrupt elements.')
                self.print('Deleting existing database...')
                tk.messagebox.showerror('Error:', 'Loading database failed...'
                                                  ' Corrupt elements.'
                                                  ' Reinitializing.')
                self.reset_db()
                if self.bar_clear != None:
                    self.bar_clear()
                self.print('Finished.')
                return None

            self.print('Finished.')
            if self.bar_clear != None:
                self.bar_clear()
            return email_list

        self.print('No emails present.')

    def store_tags(self, tags):
        data = self.load_json()
        if data is None:
            data = {}
            data['tags'] = tags
        elif 'tags' not in data:
            data['tags'] = tags
        else:
            old_tags = [ x for x in data['tags'].split(',') if not x.isspace() and x != '' ]
            new_tags = [ x for x in tags.split(',') if not x.isspace() and x != '' ]
            for tag in new_tags:
                if tag not in old_tags:
                    old_tags.append(tag)
            data['tags'] = ','.join(old_tags)

        with open(self.json_path, 'w') as f:
            json.dump(data, f)

    def store_json(self, tags):
        data = {
            'tags': tags
        }
        with open(self.json_path, 'w') as f:
            json.dump(data, f)

    def load_json(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            return data
        return None

    def tag_emails(self, key_list, tags):
        '''Tags emails in database
        Keyword arguments:
        key_list -- A list/tuple of dicts. Each dict should contain
                    * a subject (str non formatted) as dict['Subject]
                    * a date created (datetime.datetime obj) as dict['Date']
                    * a to address (str non formatted) as dict['To']
                    * a from address (str non formatted) as dict['From']
        '''
        self.print('Tagging emails...')
        if len(key_list) == 0:
            self.print('No emails to tag.')
            return False
        key_amt = 100 / len(key_list)

        for key in key_list:
            tag_info = self.manager.execute(
                'SELECT id, tags FROM emails'
                ' WHERE subject = ? AND created = ?'
                ' AND to_address = ? AND from_address = ?',
                (key['Subject'], key['Date'], key['To'], key['From']),
            ).fetchone()

            if tag_info['tags'] is not None:
                add_tags = [ x for x in tag_info['tags'].split(',') if not x.isspace() and x != '' ]
                search_tags = [ x for x in tags.split(',') if not x.isspace() and x != '']
                for tag in search_tags:
                    if tag not in add_tags:
                        add_tags.append(tag)
                str_tags = ','.join(add_tags)
            else:
                str_tags = tags

            self.manager.execute(
                'UPDATE emails SET tags = ?'
                ' WHERE subject = ? AND created = ?'
                ' AND to_address = ? AND from_address = ?',
                (str_tags, key['Subject'], key['Date'], key['To'], key['From']),
            )
            self.manager.commit()
            if self.bar != None:
                self.bar(key_amt)

        self.print('Finished.')
        if self.bar_clear != None:
            self.bar_clear()
        return True

    def get_tagged_emails(self, tags):
        '''Gets emails tagged with a tag in list/tuple (tags).
        Returns list of email, attachment file name tuples:
        ->    [(email, filename), ...]
        '''
        self.print('Loading emails...')
        counter = 1
        email_refs = self.manager.execute(
            'SELECT id, tags FROM emails'
        ).fetchall()

        new_tags = tags.split(',')
        if len(email_refs) > 0:
            email_list = []
            self.print('Getting emails...')
            for ref in email_refs:
                is_match = False
                if ref['tags'] != None:
                    ref_tags = ref['tags'].split(',')
                    for tag in ref_tags:
                        if tag in new_tags:
                            is_match = True
                            break
                
                if is_match == True:
                    email_list.append(self.get_message_details(ref))

            self.print('Finished.')
            return email_list
        self.print('Finished.')
        return False

    def get_all_emails(self):
        self.print('Loading emails...')
        counter = 1
        email_refs = self.manager.execute(
            'SELECT id, tags FROM emails'
        ).fetchall()
        if len(email_refs) > 0:
            bar_add = 100 / len(email_refs)
            email_list = []
            self.print('Getting emails...')
            for ref in email_refs:
                email_list.append(self.get_message_details(ref))
                self.bar(bar_add)

            self.bar_clear()
            return email_list

        self.print('Finished.')
        return False

    def get_message_details(self, ref):
        '''Get one email message and all of its attachments
        Keyword arguments:
        ref -- the internal database reference of the email
        '''
        attachments = self.manager.execute(
            'SELECT id, filename, extension, email_lk FROM files'
            ' WHERE email_lk = ?',
            (ref['id'],)
        ).fetchall()
        attach_ls = None
        if len(attachments) > 0:
            attach_ls = []
            for attached in attachments:
                filename = ''.join( (str(attached['id']), attached['extension']) )
                attach_ls.append(os.path.join(self.attach_path, filename))

        file_path = os.path.join(
            self.save_path,
            "".join( ( str(ref['id']), '.pkl' ) )
        )
        with open(file_path, 'rb') as f:
            return (pickle.load(f), attach_ls)