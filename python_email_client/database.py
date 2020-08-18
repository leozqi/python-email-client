import email.utils
import time
import sys
import os
import pickle
import sqlite3
import shutil
import stat
from datetime import datetime
import json
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox

# Own functions
import infos
import utils
import gui_elements

class EmailDatabase():
    def __init__(self, wait_func, print_func=print, bar_func=print):
        '''Initializes an email database.
        Keyword arguments:
            print_func -- a method outputting information to a window
            bar_func -- a method that adds an amount to a ttk.progressBar
        Path tree:
        /home
        -- /Python Email
        ---- /manager.db
        ---- /temp (temporary)
        ------ /data.html (stores webpage display)
        ---- /profiles
        ------ /[profile_ids as ints]
        -------- /saved (emails go here)
        -------- /attach (attachments go here)
        '''
        # Functions
        self.print = print_func
        self.bar = bar_func
        self.wait_func = wait_func

        # Configuration
        self.p_id = None    # Profile ID

        # Different paths
        self.resource_path = utils.get_store_path()
        if not os.path.exists(self.resource_path): os.makedirs(self.resource_path)

        self.database_path = os.path.join(self.resource_path, 'manager.db')
        self.temp_path = os.path.join(self.resource_path, 'temp/data.html')
        self.profile_path = os.path.join(self.resource_path, 'profiles/')
        self.manager = self._load_db() # sqlite3 db connection

    def __del__(self):
        try:
            if self.manager is not None:
                self.manager.close()
        except AttributeError:
            pass

        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def get_profile_info(self, title, profiles, default=None):
        '''Keyword arguments:
        title -- The title of the window
        profiles -- A list of already taken profile names that should
                    not conflict
        default -- a tuple of default values for each profile component:
                   * Profile Name
                   * Email address
                   * Password
                   * IMAP server
        '''
        popup_window = gui_elements.PopupProfileDialog(title, profiles, default)
        self.wait_func(popup_window.popup)
        return popup_window.info

    def configure_profile(self):
        p_ids = self.manager.execute(
            'SELECT id, name FROM profiles'
        ).fetchall()
        choices = [i['name'] for i in p_ids]
        choices.append('Create new...')
        popup_select = gui_elements.PopupSelectDialog('Pick a profile',
                                                      'Select profile to use this session',
                                                       choices)
        self.wait_func(popup_select.popup)
        name = popup_select.result.get()
        
        if name != 'Create new...':
            for i in p_ids:
                if i['name'] == name:
                    self.p_id = i['id']
                    break
        else:
            name = self.create_profile()

        if self.p_id is None:
            tk.messagebox.showwarning('Warning', 'No option was selected')
            self.configure_profile()
            return False
        self.update_paths()
        tk.messagebox.showinfo('Info',
                               f'You have selected profile "{name}"" as your'
                               f' profile.\nId number: {self.p_id}')

    def create_profile(self):
        profiles = self.manager.execute(
            'SELECT (name) FROM profiles'
        ).fetchall()
        new_profiles = profiles.copy()
        new_profiles.append('Create new...')
        p_info = self.get_profile_info('Create a new profile', profiles)
        while len(p_info) == 0:
            p_info = self.get_profile_info('Please fill out this form', profiles)
        self.manager.execute(
            'INSERT INTO profiles (name, email, password, imap, port)'
            ' VALUES (?, ?, ?, ?, ?)',
            (p_info[0], p_info[1], p_info[2], p_info[3], int(p_info[4])))
        self.manager.commit()
        self.p_id = self.manager.execute(
            'SELECT last_insert_rowid() FROM profiles'
        ).fetchone()[0]
        self.update_paths()
        return p_info[0]

    def edit_profile(self):
        p_ids = self.manager.execute(
            'SELECT id, name, email, password, imap FROM profiles'
        ).fetchall()
        choices = [i['name'] for i in p_ids]
        if len(choices) == 0:
            tk.messagebox.showwarning('Warning', 'No profiles to edit')
            return False
        popup_select = gui_elements.PopupSelectDialog('Pick a profile',
                                                      'Select profile to edit',
                                                       choices)
        self.wait_func(popup_select.popup)
        name = popup_select.result.get()
        change_id = None
        for i in p_ids:
            if i['name'] == name:
                change_id = i['id']
                email = i['email']
                name = i['name']
                password = i['password']
                imap = i['imap']
                break
        if change_id is None:
            tk.messagebox.showwarning('Warning', 'No option was selected')
            return False
        profile_list = choices.copy()
        try:
            profile_list.remove(name)
        except:
            pass
        p_info = self.get_profile_info('Edit profile', profile_list, (email, name,
                                                                  password, imap))
        while len(p_info) == 0:
            p_info = self.get_profile_info('Please fill out this form:'
                                           ' Edit profile', profiles)
        self.manager.execute(
            'UPDATE profiles SET name = ?, email = ?, password = ?, imap = ?, port = ?'
            ' WHERE id = ?',
            (p_info[0], p_info[1], p_info[2], p_info[3], int(p_info[4]), change_id))
        self.manager.commit()
        self.p_id = change_id
        self.update_paths()

    def update_paths(self):
        self.save_path = os.path.join(self.profile_path, f'{self.p_id}/saved/')
        if not os.path.exists(self.save_path): os.makedirs(self.save_path)
        self.attach_path = os.path.join(self.profile_path, f'{self.p_id}/attach/')
        if not os.path.exists(self.attach_path): os.makedirs(self.attach_path)
        self.last_date = self._load_last_date()

    def _load_db(self):
        '''Returns a stored SQLITE3 database. Creates one if one is not found.
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
            db.executescript(infos.SCHEMA)
            db.commit()
            return db

    def reset_db(self):
        '''Resets the database. Deletes all database contents.'''
        self.print('Resetting...')
        self.manager = None
        os.chmod(self.resource_path, stat.S_IWUSR)
        os.remove(self.database_path)
        shutil.rmtree(self.save_path)
        os.mkdir(self.save_path)
        os.chmod(self.save_path, stat.S_IWUSR)
        shutil.rmtree(self.attach_path)
        os.mkdir(self.attach_path)
        os.chmod(self.attach_path, stat.S_IWUSR)

        if os.path.exists(self.temp_path): os.remove(self.temp_path)
        self.print('Resetted database.')

    def load_profile_info(self):
        '''Returns all profile data stored for the currently loaded
        profile (whose id is stored at self.p_id)
        Returns -> data dictionary containing profile info.
        '''
        assert self.p_id is not None
        data = self.manager.execute(
            'SELECT * FROM profiles WHERE id = ?',
            (self.p_id,)
        ).fetchone()
        return data

    def save_date_now(self):
        '''Save the timestamp date of the current time'''
        assert self.p_id is not None
        self.manager.execute(
            'UPDATE profiles SET date = CURRENT_TIMESTAMP WHERE id = ?',
            (self.p_id,))
        self.manager.commit()
        return True

    def _load_last_date(self):
        '''Returns the last date that the email server was accessed.
        Returns -> datetime.datetime object or Nonetype if not found.
        '''
        assert self.p_id is not None
        data = self.manager.execute(
            'SELECT id, date FROM profiles WHERE id = ?',
            (self.p_id,)
        ).fetchone()
        if data['date'] is None:
            return None
        else:
            return data['date']

    def get_datestr(self):
        if self.last_date == None:
            return None
        else:
            return self.last_date.strftime('%d-%b-%Y')

    def save_emails(self, email_list):
        '''Saves emails into the database.
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
                    elif not part.get('Content-Disposition'):
                        continue
                    elif part.get_filename() is None:
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
                self.print('Finished.')
                return None

            self.print('Finished.')
            return email_list

        self.print('No emails present.')

    def store_tags(self, tags):
        '''Stores tags in the 'profiles' table of the database'''
        data = self.manager.execute(
            'SELECT * FROM profiles WHERE id = ?',
            (self.p_id,)
        ).fetchone()
        if data['tags'] is None:
            update_tags = tags
        else:
            update_tags = utils.merge_tags(data['tags'], tags)
        self.manager.execute(
            'UPDATE profiles SET tags = ? WHERE id = ?',
            (update_tags, self.p_id))
        self.manager.commit()

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
                str_tags = utils.merge_tags(tag_info['tags'], tags)
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