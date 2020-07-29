import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
import tkinter.scrolledtext

class ScrollingFrameAndView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.scwidth = 320
        self.canvas = tk.Canvas(self, borderwidth=0, width=self.scwidth)
        self.frame = ttk.Frame(self.canvas, width=self.scwidth)
        self.vsb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.canvas.create_window((4,4), window=self.frame, anchor='nw',
                                  tags='self.frame')
        self.frame.bind('<Configure>', self.onFrameConfigure)
        self.vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.display_frame = ttk.Labelframe(self, text='Email Text:', width=self.scwidth)
        self.display_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.display_text = tkinter.scrolledtext.ScrolledText(self.display_frame)
        self.display_text.configure(state='disabled', font=('TkDefaultFont', 12))
        self.display_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.elements = [] # container for our elements
        self.on_row = 0
        self.add_label('Emails below:')

    def add_label(self, text):
        self.elements.append(ttk.Label(self.frame, text=text))
        self.elements[-1].pack(side=tk.TOP, fill=tk.X)
        self.on_row += 1
    
    def add_button(self, label, text_to_display):
        self.elements.append(ttk.Button(self.frame, text=label,
                             command=lambda: self.display(text_to_display)))
        self.elements[-1].pack(side=tk.TOP, fill=tk.X)
        self.on_row += 1

    def display(self, text):
        self.display_text.config(state='normal')
        self.display_text.delete('1.0', 'end')
        self.display_text.insert('1.0', text)
        self.display_text.config(state='disabled')
    
    def reset_frame(self):
        for elem in self.elements:
            elem.grid_forget()
            elem.destroy()

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class OverviewPane(ttk.Panedwindow):
    def __init__(self, parent, search_func, version):
        ttk.Panedwindow.__init__(self, parent, orient=tk.VERTICAL)
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

        # Checkbuttons
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

        # Feedback
        self.search_fd_lb = ttk.Label(self.search, text='Search values:')
        self.search_fd_lb.pack(fill=tk.X)

        self.search_terms = tk.StringVar()
        self.search_terms.set(' ')
        self.search_terms_lb = ttk.Label(self.search, textvariable=self.search_terms)
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