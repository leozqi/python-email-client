import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
import tkinter.scrolledtext
import gc

# Only ScrollingFrameAndView.view_in_browser below
import webbrowser
import utils
import sys
import os

class ScrollFrame(tk.Frame):
    def __init__(self, parent, scwidth=None):
        '''Creates a scrolling frame.
        Keyword arguments:
        parent -- the frame's parent Tkinter element.
        scwidth -- width of the frame (Default is None)
        '''
        tk.Frame.__init__(self, parent)
        if scwidth is None:
            self.scwidth = 320
        else:
            self.scwidth = scwidth

        self.canvas = tk.Canvas(self, borderwidth=0, width=self.scwidth)
        self.frame = ttk.Frame(self.canvas, width=self.scwidth)
        self.vsb = tk.Scrollbar(self, orient=tk.VERTICAL,
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.canvas.create_window((0,0), window=self.frame, anchor='nw',
                                  tags='self.frame')
        self.frame.bind('<Configure>', self._on_frame_config)
        self.frame.bind('<Enter>', self._bind_mswheel)
        self.frame.bind('<Leave>', self._unbind_mswheel)
        self.vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.elements = []

    # Binds/Unbinds mousewheel to the rendering canvas
    def _bind_mswheel(self, event):
        self.canvas.bind_all('<MouseWheel>', self._on_mouse)

    def _unbind_mswheel(self, event):
        self.canvas.unbind_all('<MouseWheel>')

    def _on_mouse(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')

    def _on_frame_config(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def add_label(self, text):
        '''Adds a label to the ScrollFrame.
        Keyword arguments:
        text -- the text on the label
        '''
        self.elements.append(ttk.Label(self.frame, text=text))
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

class ScrollingFrameAndView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.config = utils.get_config()
        self.save_path = os.path.join(sys.path[0], 'resources/temp/')
        self.left_fm = ttk.Frame(self, width=320)
        self.left_fm.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.email_num = tk.StringVar()
        self.email_num.set('0 emails below:')
        self.email_lb = ttk.Label(self.left_fm, textvariable=self.email_num)
        self.email_lb.pack(fill=tk.X)
        self.scroll_frame = ScrollFrame(self.left_fm)
        self.scroll_frame.pack(fill=tk.Y, expand=True)

        self.display_frame = ttk.Labelframe(self, text='Email Text:')
        self.display_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.search_lb = ttk.Label(self.display_frame, text='Search below:')
        self.search_lb.pack(side=tk.TOP, fill=tk.X)
        self.search_txt = ttk.Entry(self.display_frame)
        self.search_txt.bind('<Return>', self.highlight_searches)
        self.search_txt.pack(side=tk.TOP, fill=tk.X)
        self.search_bt = ttk.Button(self.display_frame, text='Search for text',
                                    command=self.highlight_searches)
        self.search_bt.pack(side=tk.TOP, fill=tk.X)
        self.view_bt = ttk.Button(self.display_frame, text='View in browser',
                                  command=self.view_in_browser)
        self.view_bt.pack(side=tk.TOP, fill=tk.X)
        self.display_txt = tkinter.scrolledtext.ScrolledText(self.display_frame)
        self.display_txt.configure(state='disabled',
                                   font=('TkDefaultFont', 12))
        self.display_txt.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def add_button(self, label, text_to_display, can_view):
        self.scroll_frame.add_button(label, self.display, text_to_display,
                                     can_view)

    def display(self, text, can_view):
        if not can_view:
            self.view_bt.config(state=tk.DISABLED)
        else:
            self.view_bt.config(state=tk.NORMAL)
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
        txt = self.search_txt.get()
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

    def view_in_browser(self):
        txt = self.display_txt.get(1.0, tk.END)
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        with open(os.path.join(self.save_path, 'data.html'), 'w') as f:
            f.write(txt)

        webbrowser.open('file://' + os.path.realpath(os.path.join(self.save_path,
                                                                  'data.html')))

class OverviewPane(ttk.Panedwindow):
    def __init__(self, parent, search_func, version, tag_func, show_func):
        ttk.Panedwindow.__init__(self, parent, orient=tk.VERTICAL)
        # Overview
        self.overview = ttk.Labelframe(self, text='Overview')
        self.search_func = search_func
        self.tag_func = tag_func
        self.show_func = show_func
        self.status = tk.StringVar()
        self.status.set(
            f'PythonEmail Client version {version}.'
            '\nNo emails loaded.'
            '\nPress the "Get Emails" button to get emails.'
        )
        self.status_lb = ttk.Label(self.overview, textvariable=self.status)
        self.status_lb.pack(fill=tk.X)

        self.thread_num = tk.StringVar()
        self.thread_num.set('1')
        self.thread_lb = ttk.Label(self.overview, textvariable=self.thread_num)
        self.thread_lb.pack(fill=tk.X)
        self.show_bt = ttk.Button(self.overview, text='Show All Emails!',
                                  command=self.show_func)
        self.show_bt.pack(fill=tk.X)

        # Search functions
        self.search = ttk.Labelframe(self, text='Search')
        self.search_lb = ttk.Label(self.search,
                                   text='Enter comma separated search '
                                        'values to search for:')
        self.search_lb.pack(fill=tk.X)
        self.search_en = ttk.Entry(self.search)
        self.search_en.pack(fill=tk.X)
        self.search_bt = ttk.Button(self.search, text='Search!',
                                    command= lambda: self.search_func(
                                        self.search_en.get())
                                    )
        self.search_bt.pack(fill=tk.X)

        self.search_sub = tk.IntVar()
        self.search_to = tk.IntVar()
        self.search_from = tk.IntVar()
        self.search_all = tk.IntVar()
        self.search_sub_ch = tk.Checkbutton(self.search,
                                            text='Search subject lines?',
                                            variable=self.search_sub,
                                            onvalue=1, offvalue=0)
        self.search_sub_ch.pack()
        self.search_to_ch = tk.Checkbutton(self.search,
                                           text='Search "to" lines?',
                                           variable=self.search_to,
                                           onvalue=1, offvalue=0)
        self.search_to_ch.pack()
        self.search_from_ch = tk.Checkbutton(self.search,
                                             text='Search "from" lines?',
                                             variable=self.search_from,
                                             onvalue=1, offvalue=0)
        self.search_from_ch.pack()
        self.search_all_ch = tk.Checkbutton(self.search,
                                         text='All terms must match?',
                                         variable=self.search_all,
                                         onvalue=1, offvalue=0)
        self.search_all_ch.pack()

        self.search_fd_lb = ttk.Label(self.search, text='Search values:')
        self.search_fd_lb.pack(fill=tk.X)

        self.search_terms = tk.StringVar()
        self.search_terms.set(' ')
        self.search_terms_lb = ttk.Label(self.search,
                                         textvariable=self.search_terms)
        self.search_terms_lb.pack(fill=tk.X)

        # Tag functions
        self.previous = ttk.Labelframe(self,
                                       text='Grouped Tags:')
        self.prev_searches = ScrollFrame(self.previous, 320)
        self.prev_searches.pack()

        # Configure paned window
        self.add(self.overview)
        self.add(self.search)
        self.add(self.previous)

    def add_button(self, label, tag):
        self.prev_searches.add_button(label, self.tag_func, tag)

    def reset_frame(self):
        self.prev_searches.reset_frame()

    def set_status(self, txt):
        self.status.set(txt)

    def set_thread_cnt(self, cnt):
        self.thread_num.set(str(cnt))

    def set_search_terms(self, searches):
        string = ''
        for search in searches:
            string = "".join((string, search, '\n'))
        self.search_terms.set(string)

    def get_checkboxes(self):
        return (self.search_sub.get(), self.search_to.get(),
                self.search_from.get(), self.search_all.get())

    def get_thread_cnt(self):
        return int(self.thread_num.get())

    def clear_entry(self):
        self.search_en.delete(0, tk.END)

    def enable_search(self):
        self.search_bt.configure(state=tk.NORMAL)

    def disable_search(self):
        self.search_bt.configure(state=tk.DISABLED)

class OverMenu(tk.Menu):
    def __init__(self, parent, conv_func, reset_func, version):
        tk.Menu.__init__(self, parent)
        self.version = version
        self.conv_func = conv_func
        self.reset_func = reset_func
        self.add_command(label='Refresh Mailbox', 
                         command=self.conv_func)

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
                    '\nVersion: ' + self.version)