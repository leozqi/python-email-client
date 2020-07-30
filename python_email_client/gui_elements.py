import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
import tkinter.scrolledtext
# Only ScrollingFrameAndView.view_in_browser
import webbrowser
import utils
import sys
import os

class ScrollingFrameAndView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.config = utils.get_config()
        self.save_path = os.path.join(sys.path[0], 'resources/temp/')
        self.scwidth = 320
        self.canvas = tk.Canvas(self, borderwidth=0, width=self.scwidth)
        self.frame = ttk.Frame(self.canvas, width=self.scwidth)
        self.vsb = tk.Scrollbar(self, orient=tk.VERTICAL,
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.canvas.create_window((4,4), window=self.frame, anchor='nw',
                                  tags='self.frame')
        self.frame.bind('<Configure>', self.onFrameConfigure)
        self.frame.bind('<Enter>', self._bind_to_mousewheel)
        self.frame.bind('<Leave>', self._unbind_to_mousewheel)
        self.vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.display_frame = ttk.Labelframe(self, text='Email Text:',
                                            width=self.scwidth)
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

        self.elements = [] # container for our elements
        self.on_row = 0
        self.add_label('Emails below:')

    def _bind_to_mousewheel(self, event):
        self.canvas.bind_all('<MouseWheel>', self._on_mouse)

    def _unbind_to_mousewheel(self, event):
        self.canvas.unbind_all('<MouseWheel>')

    def _on_mouse(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')

    def add_label(self, text):
        self.elements.append(ttk.Label(self.frame, text=text))
        self.elements[-1].pack(side=tk.TOP, fill=tk.X)
        self.on_row += 1
    
    def add_button(self, label, text_to_display, can_view):
        self.elements.append(ttk.Button(self.frame, text=label,
                             command=lambda: self.display(text_to_display, can_view)))
        self.elements[-1].pack(side=tk.TOP, fill=tk.X)
        self.on_row += 1

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
        while len(self.elements) > 0:
            self.elements[-1].grid_forget()
            self.elements[-1].destroy()
            del self.elements[-1]

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

        webbrowser.open('file://' + os.path.realpath(os.path.join(self.save_path, 'data.html')))

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class OverviewPane(ttk.Panedwindow):
    def __init__(self, parent, search_func, version):
        ttk.Panedwindow.__init__(self, parent, orient=tk.VERTICAL)
        # Overview
        self.overview = ttk.Labelframe(self, text='Overview')
        self.search_func = search_func
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

        # Search functions
        self.search = ttk.Labelframe(self, text='Search')
        self.search_lb = ttk.Label(self.search,
                                   text='Enter comma separated tag '
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

        self.search_fd_lb = ttk.Label(self.search, text='Search values:')
        self.search_fd_lb.pack(fill=tk.X)

        self.search_terms = tk.StringVar()
        self.search_terms.set(' ')
        self.search_terms_lb = ttk.Label(self.search,
                                         textvariable=self.search_terms)
        self.search_terms_lb.pack(fill=tk.X)

        # Configure paned window
        self.add(self.overview)
        self.add(self.search)
    
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
                self.search_from.get())

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
        self.add_command(label='Get Mail!', 
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