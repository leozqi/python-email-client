import tkinter as tk
from tkinter import ttk
import tkinter.scrolledtext

class ScrollingFrameAndView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.scwidth = 350
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