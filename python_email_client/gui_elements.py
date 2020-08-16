import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
import tkinter.scrolledtext
import gc
import infos

# Only ScrollingFrameAndView.view_in_browser below
import webbrowser
import utils
import sys
import os

# Only ScrollingFrameAndView.view_attached below
import subprocess

def center(toplevel):
    toplevel.update_idletasks()

    screen_width = toplevel.winfo_screenwidth()
    screen_height = toplevel.winfo_screenheight()

    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    x = screen_width/2 - size[0]/2
    y = screen_height/2 - size[1]/2

    toplevel.geometry("+%d+%d" % (x, y))

class ScrollFrame(tk.Frame):
    def __init__(self, parent, scwidth=None):
        '''Creates a scrolling frame.
        Keyword arguments:
        parent -- the frame's parent Tkinter element.
        scwidth -- width of the frame (Default is None)
        '''
        tk.Frame.__init__(self, parent)
        self.scwidth = scwidth

        if self.scwidth is None:
            self.canvas = tk.Canvas(self, borderwidth=0)
            self.frame = ttk.Frame(self.canvas)
        else:
            self.canvas = tk.Canvas(self, borderwidth=0, width=self.scwidth)
            self.frame = ttk.Frame(self.canvas, width=self.scwidth)

        self.vsb = tk.Scrollbar(self, orient=tk.VERTICAL,
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        if self.scwidth is None:
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        else:
            self.canvas.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas.create_window((0,0), window=self.frame, anchor='nw',
                                  tags='self.frame')
        self.frame.bind('<Configure>', self._on_frame_config)
        self.frame.bind('<Enter>', self._bind_mswheel)
        self.frame.bind('<Leave>', self._unbind_mswheel)
        self.vsb.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.elements = []

    # Binds/Unbinds mousewheel to the rendering canvas
    def _bind_mswheel(self, event):
        self.canvas.bind_all('<MouseWheel>', self._on_mouse)

    def _unbind_mswheel(self, event):
        self.canvas.unbind_all('<MouseWheel>')

    def _on_mouse(self, event):
        if self.frame_h >= self.canvas_h:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')

    def _on_frame_config(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.frame.update_idletasks()
        self.canvas.update_idletasks()
        self.frame_h = self.frame.winfo_height()
        self.canvas_h = self.canvas.winfo_height()

    def add_label(self, text):
        '''Adds a label to the ScrollFrame.
        Keyword arguments:
        text -- the text on the label
        '''
        self.elements.append(ttk.Label(self.frame, text=tfext))
        self.elements[-1].pack(side=tk.TOP, fill=tk.X)

    def add_button(self, text, command, *args):
        '''Adds a button to the ScrollFrame. Must have a pressed cmd.
        Keyword arguments:
        text -- the text on the button
        command -- a function which must not depend on any input other 
                   than its arguments
        *args -- the arguments of the command function in order.
        '''
        if len(args) == 0:
            self.elements.append(ttk.Button(self.frame, text=text,
                                 command=command))
        else:
            self.elements.append(ttk.Button(self.frame, text=text,
                                 command=lambda: command(*args)))

        self.elements[-1].pack(side=tk.TOP, fill=tk.X)

    def reset_frame(self):
        '''Resets the frame.'''
        self.vsb.set(0, 0)
        while len(self.elements) > 0:
            self.elements[-1].grid_forget()
            self.elements[-1].destroy()
            del self.elements[-1]
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        gc.collect()

class ScrollText(tk.scrolledtext.ScrolledText):
    def __init__(self, parent):
        tk.scrolledtext.ScrolledText.__init__(self, parent)
        self.config(state='disabled',
                    font=('TkDefaultFont', 12))
    
    def show_txt(self, text):
        if text is None:
            text = default

        self.config(state='normal')
        self.delete('1.0', 'end')
        self.insert('1.0', text)
        self.config(state='disabled')
    
    def clear_txt(self):
        self.config(state='normal')
        self.delete('1.0', 'end')
        self.config(state='disabled')

class PopupDialog(tk.Toplevel):
    def __init__(self, title='Dialog', geometry='600x100'):
        '''Creates a popup dialog.
        Keyword arguments:
        geometry -- the width of the window, as a string: eg '1920x1680'
        '''
        tk.Toplevel.__init__(self)
        self.geometry(geometry)
        self.title(title)
        self.iconbitmap('favicon.ico')
        self.resizable(width=False, height=False)
        center(self)
        self.update_idletasks()
    
    def delete(self):
        self.update_idletasks()
        for child in self.winfo_children():
            child.destroy()
        self.destroy()

class ScrollingFrameAndView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.save_path = os.path.join(utils.get_store_path(), 'resources/temp/')
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        self.left_fm = ttk.Frame(self, width=320)
        self.left_fm.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.email_num = tk.StringVar()
        self.email_num.set('0 emails below:')
        self.email_lb = ttk.Label(self.left_fm, textvariable=self.email_num)
        self.email_lb.pack(fill=tk.X)
        self.scroll_frame = ScrollFrame(self.left_fm, 320)
        self.scroll_frame.pack(fill=tk.Y, expand=True)

        self.display_frame = ttk.Labelframe(self, text='Email Viewer:')

        self.email_info_sv = tk.StringVar()
        self.email_info_sv.set('Email Information:')
        self.email_info_lb = ttk.Label(self.display_frame,
                                       textvariable=self.email_info_sv)
        self.email_info_lb.pack(fill=tk.X)

        # Text search function
        self.search_f = ttk.Frame(self.display_frame)
        self.search_lb = ttk.Label(self.search_f, text='Find words in email:')
        self.search_lb.pack(side=tk.LEFT)
        self.search_en = ttk.Entry(self.search_f)
        self.search_en.bind('<Return>', self.highlight_searches)
        self.search_en.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_bt = ttk.Button(self.search_f, text='Search for text',
                                    command=self.highlight_searches)
        self.search_bt.pack(side=tk.LEFT)
        self.search_f.pack(fill=tk.X)

        self.view_bt = ttk.Button(self.display_frame, text='View in browser',
                                  command=self.view_in_browser)
        self.view_bt.pack(fill=tk.X)
        self.display_txt = tk.scrolledtext.ScrolledText(self.display_frame)
        self.display_txt.configure(state='disabled',
                                   font=('TkDefaultFont', 12))
        self.display_txt.pack(fill=tk.BOTH, expand=True)
        self.attachment_bt = ttk.Button(self.display_frame,
                                        text='Open attachment(s)',
                                        command=self.view_attached)
        self.attachment_bt.pack(fill=tk.X)
        self.display_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor='nw')

        self.attachment_display = ScrollFrame(self.display_frame)
        self.attachment_display.pack(fill=tk.X)

    def add_email_info(self, **kwargs):
        email_info = 'Email information:\n'
        for key, value in kwargs.items():
            email_info = ''.join( (email_info, f'{key}: {value}\n' ) )
        
        self.email_info_sv.set(email_info)

    def add_button(self, label, text_to_display, can_view, attach_ids=None,
                   email_info={}):
        self.scroll_frame.add_button(label, self.display, text_to_display,
                                     can_view, attach_ids, email_info)

    def display(self, text, can_view, attach_ids, email_info):
        '''Displays email information.
        Keyword arguments:
        email_info -- must be a dict of key/pair arguments for email information.
        '''
        if not can_view:
            self.view_bt.config(state=tk.DISABLED)
        else:
            self.view_bt.config(state=tk.NORMAL)
        
        if attach_ids:
            self.attach_ids = attach_ids
            self.attachment_bt.config(state=tk.NORMAL)
        else:
            self.attachment_bt.config(state=tk.DISABLED)

        self.add_email_info(**email_info)
        if text is None:
            text = '<<This email has no text -- Python Email Client Message>>'

        self.display_txt.config(state='normal')
        self.display_txt.delete('1.0', 'end')
        self.display_txt.insert('1.0', text)
        self.display_txt.config(state='disabled')

    def reset_frame(self):
        self.scroll_frame.reset_frame()

    def update_cnt(self):
        '''Updates the count of the amount of emails in frame'''
        self.email_num.set(f'{len(self.scroll_frame.elements)} emails below:')

    def highlight_searches(self, event=None):
        self.display_txt.tag_remove('found', '1.0', tk.END)
        txt = self.search_en.get()
        if txt:
            pos = '1.0'
            count = 0
            while True:
                pos = self.display_txt.search(txt, pos, nocase=1,
                                              stopindex=tk.END)
                if not pos:
                    break
                last_pos = '%s+%dc' % (pos, len(txt))
                self.display_txt.tag_add('found', pos, last_pos)
                pos = last_pos
                self.display_txt.see(pos)
                count += 1
            self.display_txt.tag_config('found', background='yellow')
            if count == 0:
                tk.messagebox.showwarning('Warning:', 'No search results found.')
                return False
            self.display_txt.focus_set()
            return True
        tk.messagebox.showwarning('Warning', 'No search specified.')

    def view_in_browser(self):
        txt = self.display_txt.get(1.0, tk.END)
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        with open(os.path.join(self.save_path, 'data.html'), 'w') as f:
            f.write(txt)

        webbrowser.open('file://' + os.path.realpath(os.path.join(self.save_path,
                                                                  'data.html')))

    def view_attached(self):
        if self.attach_ids is None:
            tk.messagebox.showerror('Error', 'No attachments to display.')
            return False

        tk.messagebox.showinfo('Info', 'Opening attached file(s) with a default'
                                       ' system application.')
        for filename in self.attach_ids:
            if sys.platform == 'linux2':
                subprocess.call(["xdg-open", filename])
            else:
                os.startfile(filename)

class OverMenu(tk.Menu):
    def __init__(self, parent, reset_func):
        tk.Menu.__init__(self, parent)
        self.reset_func = reset_func

        self.advmenu = tk.Menu(self, tearoff=0)
        self.advmenu.add_command(label='Reset Database',
                                 command=self.reset_func)

        self.helpmenu = tk.Menu(self, tearoff=0)
        self.helpmenu.add_command(label='About', command=self.about)

        self.add_cascade(label='Advanced', menu=self.advmenu)
        self.add_cascade(label='Help', menu=self.helpmenu)

    def about(self):
        tk.messagebox.showinfo(
            'About', 
            message='Made by Leo Qi!'
                    '\nVersion: ' + config.VERSION)

class PopupProfileDialog():
    def __init__(self, title, profiles, default=None):
        self.popup = PopupDialog(title=title, geometry='600x200')
        labels = ['Profile Name (alphanumeric): ',
                  'Email address: ',
                  'Password: ',
                  'IMAP server: ',
                  'IMAP server port (default 993): ']
        self.dialog_labels = []
        self.dialog_entries = []
        self.dialog_frames = []
        self.info = []

        for label in labels:
            self.dialog_frames.append(ttk.Frame(self.popup))
            self.dialog_frames[-1].pack(fill=tk.X)
            self.dialog_labels.append(ttk.Label(self.dialog_frames[-1],
                                                text=label,
                                                width=34))
            self.dialog_labels[-1].pack(side=tk.LEFT)
            self.dialog_entries.append(ttk.Entry(self.dialog_frames[-1]))
            self.dialog_entries[-1].pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.spacer = ttk.Label(self.popup, text=' ')
        self.spacer.pack()
        self.submit_bt = ttk.Button(self.popup, text='Submit',
                                    command=lambda: self.validate_profile(
                                    self.dialog_entries, profiles))
        self.submit_bt.pack()
        
        if default is not None and len(default) <= 4:
            for n in range(len(default)):
                self.dialog_entries[n].insert(0, default[n])

        self.dialog_entries[4].insert(0, '993')

    def validate_profile(self, entries, profiles):
        entry_values = []
        for entry in entries:
            entry_values.append(entry.get())

        if utils.is_whitespace(entry_values[0]) or (entry_values[0] in profiles):
            tk.messagebox.showerror('Error', 'The profile name must be unique'
                                             ' and not blank.')
            entries[0].delete(0, tk.END)
            self.popup.lift()
            return False

        if ( (not '@' in entry_values[1]) or utils.is_whitespace(entry_values[1])
                or (' ' in entry_values[1]) ):
            tk.messagebox.showerror('Error', 'Email address field must be valid'
                                             ' and without spaces.')
            entries[1].delete(0, tk.END)
            self.popup.lift()
            return False

        if utils.is_whitespace(entry_values[2]):
            tk.messagebox.showerror('Error', 'Password field must not be blank.')
            entries[2].delete(0, tk.END)
            self.popup.lift()
            return False

        if utils.is_whitespace(entry_values[3]) or (' ' in entry_values[3]):
            tk.messagebox.showerror('Error', 'IMAP server address must be valid.')
            entries[3].delete(0, tk.END)
            self.popup.lift()
            return False

        if not entry_values[4].isdigit():
            tk.messagebox.showerror('Error', 'IMAP port must be all digits.')
            entries[4].delete(0, tk.END)
            self.popup.lift()
            return False

        self.info = (*entry_values, ) # unpack into tuple
        self.popup.delete()
        return True

class PopupSelectDialog():
    def __init__(self, title, choices):
        self.popup = PopupDialog(title=title, geometry='400x100')
        self.result = tk.StringVar()
        self.result.set(' ')
        self.label = ttk.Label(self.popup,
                               text='Select profile to use this session')
        self.label.pack(fill=tk.X)
        self.combo = ttk.Combobox(self.popup, textvariable=self.result,
                                  values=choices)
        self.combo.config(state='readonly')
        self.combo.pack(fill=tk.X)
        self.submit_bt = ttk.Button(self.popup, text='Submit', command=self.submit)
        self.submit_bt.pack()

    def submit(self):
        if self.result == ' ':
            tk.messagebox.showerror('Error', 'No choice selected.')
            return False

        self.popup.delete()
        return True