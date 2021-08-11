#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#  in conjunction with Tcl version 8.6
#    Dec 27, 2019 02:47:52 PM CST  platform: Windows NT
"""
restplus support:
left file tree to organize all rest requests
batch import/export requests to/from app
basic auth on request
"""
import collections
import functools
import json
import os
import re
import reprlib
import sys
from time import time

import requests

try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

try:
    import ttk

    py3 = False
except ImportError:
    import tkinter.ttk as ttk

    py3 = True

from tkinter import filedialog, messagebox

w = None
root = None
RE_IP = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
OPER_DIR = 'C:\\jupiter\\'
VARS_FILE = 'vars.json'
CERT_FILE = 'cert.json'
DATA_FILE = 'data.json'
TEMP_FILE = 'temp.json'

DEF_FONT = ('Consolas', 10)

WIN_WIDTH = 1600
WIN_HEIGHT = 900


def prepare():
    if not os.path.exists(OPER_DIR):
        os.mkdir(OPER_DIR)
    global WIN_HEIGHT, WIN_WIDTH
    WIN_WIDTH = root.winfo_screenwidth()
    WIN_HEIGHT = root.winfo_screenheight() - 70
    print(WIN_WIDTH, WIN_HEIGHT)


def vp_start_gui():
    """Starting point when module is the main routine."""
    global val, w, root
    root = tk.Tk()
    prepare()
    top = mainFrame(root)
    root.mainloop()


def create_mainFrame(root, *args, **kwargs):
    """Starting point when module is imported by another program."""
    global w, w_win, rt
    rt = root
    w = tk.Toplevel(root)
    top = mainFrame(w)
    return (w, top)


def destroy_mainFrame():
    global w
    w.destroy()
    w = None


class AbsDialog(tk.Toplevel):
    def __init__(self, title='dialog', x=None, y=None, width=None, height=None):
        super().__init__()
        self.title(title)
        win_width = root.winfo_width()
        win_height = root.winfo_height()
        if not width:
            width = 450
        if not height:
            height = 250
        if not x:
            x = int(root.winfo_x() + win_width / 2 - width / 2)
        if not y:
            y = int(root.winfo_y() + win_height / 2 - height)
        self.geometry(str(width) + 'x' + str(height) + '+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)


class ObtainValueDialog(AbsDialog):
    def __init__(self, title, dic):
        self.dic = dic
        label_len = max([len(item) for item in dic.keys()]) + 2
        width = 200
        height = len(dic) * 15 + 55
        super().__init__(title, None, None, width, height)
        entries = []
        for key, value in dic.items():
            row = ttk.Frame(self)
            row.pack(fill="x")
            ttk.Label(row, text=key + '：', width=label_len).pack(side=tk.LEFT)
            setattr(self, key, tk.StringVar())
            entry = ttk.Entry(row, textvariable=getattr(self, key), width=40)
            if value:
                getattr(self, key).set(value)
            entry.configure(font=DEF_FONT)
            entry.pack(side=tk.LEFT)
            entries.append(entry)
        entries[0].focus_set()
        entries[len(entries) - 1].bind('<Return>', func=self.ok)

        self.configure(bg='#d9d9d9')
        row = ttk.Frame(self)
        row.pack(fill="x", side=tk.BOTTOM)
        ttk.Button(row, text="ok", command=self.ok).pack(side=tk.RIGHT)
        ttk.Button(row, text="cancel", command=self.ok).pack(side=tk.RIGHT)

        self.result = {}

    def get(self):
        return self.result

    def ok(self, ev=None):
        self.result = {item: getattr(self, item).get() for item in self.dic.keys()}
        self.destroy()

    def cancel(self):
        self.destroy()


class TreeViewDialog(AbsDialog):
    def __init__(self, title, columns, values):
        self.key_list = []
        self.default_val = ['...' for i in range(len(columns))]
        width = len(columns) * 200
        super().__init__(title, None, None, width, 300)

        self.treeview = ScrolledTreeView(self, height=100, show="headings", columns=columns)  # 表格
        for column in columns:
            self.treeview.column(column, width=200, anchor='center')
            self.treeview.heading(column, text=column)

        self.treeview.pack(fill='both')
        self.treeview.focus_set()
        for index, value in enumerate(values):
            self.treeview.insert('', tk.END, index, values=value)
            self.key_list.append(index)

        self.treeview.bind('<Double-1>', self.set_cell_value)
        self.treeview.bind('<Button-3>', func=self.on_right_click)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.result = []

    def get(self):
        return self.result

    def on_closing(self):
        print('close')

        for item in self.key_list:
            item_text = self.treeview.item(item, "values")
            self.result.append(item_text)
        self.destroy()

    def on_right_click(self, event):
        items = self.treeview.selection()
        menubar = tk.Menu(self, tearoff=False)
        menubar.delete(0, tk.END)
        menubar.add_command(label='new row', command=self.new_row)
        if items:
            menubar.add_separator()
            menubar.add_command(label='delete', command=functools.partial(self.delete_selected, items))
        menubar.post(event.x_root, event.y_root)

    def new_row(self):
        print('insert')
        index = max(self.key_list) + 1 if self.key_list else 0
        self.treeview.insert('', tk.END, index, values=self.default_val)
        self.treeview.update()
        self.key_list.append(index)

    def delete_selected(self, items):
        for item in items:
            self.treeview.delete(item)
            self.key_list.remove(int(item))

    def set_cell_value(self, event):  # 双击进入编辑状态
        for item in self.treeview.selection():
            # item = I001
            item_text = self.treeview.item(item, "values")
            # print(item_text[0:2])  # 输出所选行的值
        column = self.treeview.identify_column(event.x)  # 列
        row = self.treeview.identify_row(event.y)  # 行
        print(column)
        print(row)
        cn = int(str(column).replace('#', ''))
        rn = self.key_list.index(int(str(row).replace('I', '')))
        entry_edit = tk.Text(self, width=16, height=1)
        entry_edit.place(x=30 + (cn - 1) * 200, y=24 + rn * 20)

        def save_edit():
            self.treeview.set(item, column=column, value=entry_edit.get(0.0, "end").strip())
            entry_edit.destroy()
            okb.destroy()

        okb = ttk.Button(self, text='OK', width=4, command=save_edit)
        okb.place(x=150 + (cn - 1) * 200, y=19 + rn * 20)


class CertDialog(AbsDialog):
    def __init__(self, title, columns, values):
        self.key_list = []
        self.default_val = ['...' for i in range(len(columns))]
        width = len(columns) * 200
        win_width = root.winfo_width()
        super().__init__(title, int(win_width / 2), None, width, 400)
        self.resizable(0, 0)
        self.treeview = ScrolledTreeView(self, height=100, show="headings", columns=columns)  # 表格
        for column in columns:
            self.treeview.column(column, width=200, anchor='center')
            self.treeview.heading(column, text=column)

        self.treeview.pack(fill='both')
        self.treeview.focus_set()
        for index, value in enumerate(values):
            self.treeview.insert('', tk.END, index, values=value)
            self.key_list.append(index)

        self.treeview.bind('<Double-1>', self.set_cell_value)
        self.treeview.bind('<Button-3>', func=self.on_right_click)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.result = []

    def get(self):
        return self.result

    def on_closing(self):
        print('close')

        for item in self.key_list:
            item_text = self.treeview.item(item, "values")
            self.result.append(item_text)
        self.destroy()

    def on_right_click(self, event):
        items = self.treeview.selection()
        menubar = tk.Menu(self, tearoff=False)
        menubar.delete(0, tk.END)
        menubar.add_command(label='new row', command=self.new_row)
        if items:
            menubar.add_separator()
            menubar.add_command(label='delete', command=functools.partial(self.delete_selected, items))
        menubar.post(event.x_root, event.y_root)

    def new_row(self):
        print('insert')
        index = max(self.key_list) + 1 if self.key_list else 0
        self.treeview.insert('', tk.END, index, values=self.default_val)
        self.treeview.update()
        self.key_list.append(index)

    def delete_selected(self, items):
        for item in items:
            self.treeview.delete(item)
            self.key_list.remove(int(item))

    def set_cell_value(self, event):  # 双击进入编辑状态
        file_val = ''

        def get_val(label, ev):
            nonlocal file_val
            file_val = filedialog.askopenfilename(title='select the cert file',
                                                  filetypes=[('*', '*.cert'), ('*', '*.key'), ('*', '*.cer'),
                                                             ('*', '*.pem')])
            label.configure(text=file_val)

        for item in self.treeview.selection():
            item_text = self.treeview.item(item, "values")
        column = self.treeview.identify_column(event.x)  # 列
        row = self.treeview.identify_row(event.y)  # 行
        print(column)
        print(row)
        cn = int(str(column).replace('#', ''))
        rn = self.key_list.index(int(str(row).replace('I', '')))
        if cn == 2 or cn == 3:
            entry_edit = ttk.Label(self, text='...', width=16)
            entry_edit.bind('<Button-1>', func=functools.partial(get_val, entry_edit))
        else:
            entry_edit = tk.Text(self, width=16, height=1)
        entry_edit.place(x=30 + (cn - 1) * 200, y=24 + rn * 20)

        def save_edit(col):
            if col == 1:
                self.treeview.set(item, column=column, value=entry_edit.get(0.0, 'end').strip())
            else:
                self.treeview.set(item, column=column, value=file_val.strip())
            entry_edit.destroy()
            okb.destroy()

        okb = ttk.Button(self, text='OK', width=4, command=functools.partial(save_edit, cn))
        okb.place(x=150 + (cn - 1) * 200, y=19 + rn * 20)


class ToolTip(tk.Toplevel):
    """
    Provides a ToolTip widget for Tkinter.
    To apply a ToolTip to any Tkinter widget, simply pass the widget to the
    ToolTip constructor
    """

    def __init__(self, wdgt, tooltip_font, msg=None, msgFunc=None,
                 delay=0.5, follow=True):
        """
        Initialize the ToolTip

        Arguments:
          wdgt: The widget this ToolTip is assigned to
          tooltip_font: Font to be used
          msg:  A static string message assigned to the ToolTip
          msgFunc: A function that retrieves a string to use as the ToolTip text
          delay:   The delay in seconds before the ToolTip appears(may be float)
          follow:  If True, the ToolTip follows motion, otherwise hides
        """
        self.wdgt = wdgt
        # The parent of the ToolTip is the parent of the ToolTips widget
        self.parent = self.wdgt.master
        # Initalise the Toplevel
        tk.Toplevel.__init__(self, self.parent, bg='black', padx=1, pady=1)
        # Hide initially
        self.withdraw()
        # The ToolTip Toplevel should have no frame or title bar
        self.overrideredirect(True)

        # The msgVar will contain the text displayed by the ToolTip
        self.msgVar = tk.StringVar()
        if msg is None:
            self.msgVar.set('No message provided')
        else:
            self.msgVar.set(msg)
        self.msgFunc = msgFunc
        self.delay = delay
        self.follow = follow
        self.visible = 0
        self.lastMotion = 0
        # The text of the ToolTip is displayed in a Message widget
        tk.Message(self, textvariable=self.msgVar, bg='#FFFFDD',
                   font=tooltip_font,
                   aspect=1000).grid()

        # Add bindings to the widget.  This will NOT override
        # bindings that the widget already has
        self.wdgt.bind('<Enter>', self.spawn, '+')
        self.wdgt.bind('<Leave>', self.hide, '+')
        self.wdgt.bind('<Motion>', self.move, '+')

    def spawn(self, event=None):
        """
        Spawn the ToolTip.  This simply makes the ToolTip eligible for display.
        Usually this is caused by entering the widget

        Arguments:
          event: The event that called this funciton
        """
        self.visible = 1
        # The after function takes a time argument in miliseconds
        self.after(int(self.delay * 1000), self.show)

    def show(self):
        """
        Displays the ToolTip if the time delay has been long enough
        """
        if self.visible == 1 and time() - self.lastMotion > self.delay:
            self.visible = 2
        if self.visible == 2:
            self.deiconify()

    def move(self, event):
        """
        Processes motion within the widget.
        Arguments:
          event: The event that called this function
        """
        self.lastMotion = time()
        # If the follow flag is not set, motion within the
        # widget will make the ToolTip disappear
        #
        if self.follow is False:
            self.withdraw()
            self.visible = 1

        # Offset the ToolTip 10x10 pixes southwest of the pointer
        self.geometry('+%i+%i' % (event.x_root + 20, event.y_root - 10))
        try:
            # Try to call the message function.  Will not change
            # the message if the message function is None or
            # the message function fails
            self.msgVar.set(self.msgFunc())
        except:
            pass
        self.after(int(self.delay * 1000), self.show)

    def hide(self, event=None):
        """
        Hides the ToolTip.  Usually this is caused by leaving the widget
        Arguments:
          event: The event that called this function
        """
        self.visible = 0
        self.withdraw()


class ReqNoteBook:
    def __init__(self, top, request=None):
        if request:
            self.request = request
        else:
            self.request = dict({'method': 'get', 'url': '', 'params': {},
                                 'headers': {},
                                 'req': '', 'resp': '',
                                 'respHeaders': '', 'auth': []})

        self.top = top
        self.methodCombobox = ttk.Combobox(top)
        self.methodCombobox.place(relx=0, rely=0.008, relheight=0.03
                                  , relwidth=0.05)
        self.method_list = ['get', 'post', 'delete', 'patch', 'put']
        self.methodCombobox.configure(values=self.method_list, takefocus="", cursor="fleur", font=DEF_FONT,
                                      state="readonly")

        self.urlEntry = ttk.Entry(top)
        self.urlEntry.place(relx=0.053, rely=0.008, relheight=0.03
                            , relwidth=0.86)
        self.urlEntry.configure(takefocus="", cursor="ibeam", font=DEF_FONT)

        self.headerButton = ttk.Button(top)
        self.headerButton.place(relx=0.92, rely=0.005, height=30, width=57)
        self.headerButton.configure(takefocus="", cursor="arrow", text='''headers''')

        self.sendButton = ttk.Button(top)
        self.sendButton.place(relx=0.96, rely=0.005, height=30, width=57)
        self.sendButton.configure(takefocus="", cursor="arrow", text='''send''')

        s = ttk.Style()
        s.configure('blue.TSeparator', background='blue')
        s.configure('green.TSeparator', background='green')
        s.configure('red.TSeparator', background='red')
        ttk.Separator(top).place(relx=0, rely=0.05, relwidth=1)

        self.requestText = ScrolledText(top)
        self.requestText.place(relx=0, rely=0.08, relheight=0.92
                               , relwidth=0.5)
        self.requestText.configure(background="white", font=DEF_FONT, foreground="black",
                                   highlightbackground="#d9d9d9", highlightcolor="black", insertbackground="black",
                                   insertborderwidth="3", selectbackground="#c4c4c4", selectforeground="black",
                                   wrap="none")

        self.respHeaderText = ScrolledText(top)
        self.respHeaderText.place(relx=0.5, rely=0.08, relheight=0.12
                                  , relwidth=0.5)
        self.respHeaderText.configure(background="white", font=DEF_FONT, foreground="black",
                                      highlightbackground="#d9d9d9", highlightcolor="black", insertbackground="black",
                                      insertborderwidth="3", selectbackground="#c4c4c4", selectforeground="black",
                                      wrap="none")

        self.responseText = ScrolledText(top)
        self.responseText.place(relx=0.5, rely=0.2, relheight=0.8
                                , relwidth=0.5)
        self.responseText.configure(background="white", font=DEF_FONT, foreground="black",
                                    highlightbackground="#d9d9d9", highlightcolor="black", insertbackground="black",
                                    insertborderwidth="3", selectbackground="#c4c4c4", selectforeground="black",
                                    wrap="none")

        self.reqLabel = ttk.Label(top)
        self.reqLabel.place(relx=0.05, rely=0.055, height=18, width=60)
        self.reqLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                text='''request''')

        self.respLabel = ttk.Label(top)
        self.respLabel.place(relx=0.57, rely=0.055, height=18, width=60)
        self.respLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                 text='''response''')
        self.respCodeLabel = ttk.Label(top)
        self.respCodeLabel.place(relx=0.65, rely=0.055, height=18, width=60)
        self.respCodeLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                     text='''--''')

        self.binding_event()

        self.display_request(self.request)

    def update_data(self, dic):
        self.request.update(dic)

    def binding_event(self):
        try:
            self.methodCombobox.current(0)
            self.urlEntry.insert(0, 'http/https...')
            self.urlEntry.bind('<Return>', self.sendButton_onClick)
            self.sendButton.configure(command=self.sendButton_onClick)
            self.headerButton.configure(command=self.headerButton_onClick)
            ToolTip(self.headerButton, DEF_FONT, msg=self.tooltip_header_text(), msgFunc=self.tooltip_header_text)
        except BaseException as e:
            messagebox.showerror('error', 'fatal error occurs:' + str(e))

    def tooltip_url_text(self):
        url = self.urlEntry.get()
        var_replaced = []
        if os.path.exists(OPER_DIR + VARS_FILE):
            with open(OPER_DIR + VARS_FILE, 'r') as fp:
                var_replaced = json.load(fp)
        if var_replaced:
            for item in var_replaced:
                k, v = item[0], item[1]
                print(k, v)
                rk = '$' + str(k) + '$'
                url = url.replace(rk, v)
        return url

    def tooltip_header_text(self):
        return '\n'.join([k + ':' + v for k, v in self.request['headers'].items()])

    def headerButton_onClick(self):

        dialog = TreeViewDialog('edit headers', ['key', 'value'], [(k, v) for k, v in self.request['headers'].items()])
        self.top.wait_window(dialog)
        print(dialog.get())
        for i in dialog.get():
            self.request['headers'][i[0]] = i[1]
        print(self.request)

    def display_request(self, req):
        self.methodCombobox.set(req['method'])
        self.urlEntry.delete("0", len(self.urlEntry.get()))
        self.urlEntry.insert(0, req['url'])
        self.requestText.delete("1.0", "end-1c")
        self.requestText.insert('1.0', req['req'])
        self.respCodeLabel = ttk.Label(self.top)
        self.respCodeLabel.place(relx=0.65, rely=0.055, height=18, width=60)
        self.respCodeLabel.configure(background="#fcf7f3", foreground="black", font=DEF_FONT, relief="flat",
                                     text=req.get('respCode', '--'))

        self.respHeaderText.delete("1.0", "end-1c")
        self.respHeaderText.insert('1.0', req['respHeaders'])
        self.responseText.delete("1.0", "end-1c")
        self.responseText.insert('1.0', req['resp'])

    def request_to_json(self):
        dic = {'method': self.methodCombobox.get(), 'url': self.urlEntry.get(),
               'headers': self.request['headers'],
               'req': self.requestText.get("1.0", "end-1c"), 'resp': self.responseText.get("1.0", "end-1c"),
               'respHeaders': self.respHeaderText.get("1.0", "end-1c"), 'respCode': self.respCodeLabel.cget('text')}
        print(dic)
        self.request.update(dic)
        return self.request

    def on_send_show(self, step='0', code="--"):
        self.respCodeLabel = ttk.Label(self.top)
        self.respCodeLabel.place(relx=0.65, rely=0.055, height=15, width=60)
        if step == 'success':

            ttk.Separator(self.top, style='green.TSeparator').place(relx=0, rely=0.05, relwidth=1)
            self.respCodeLabel.configure(background="#fcf7f3", foreground="green", font=DEF_FONT, relief="flat",
                                         text=code)
            self.respHeaderText.configure(fg='green')
        elif step == 'fail':
            self.respCodeLabel.configure(background="#fcf7f3", foreground="red", font=DEF_FONT, relief="flat",
                                         text=code)
            self.respHeaderText.configure(fg='red')
            ttk.Separator(self.top, style='red.TSeparator').place(relx=0, rely=0.05, relwidth=1)
        else:
            ttk.Separator(self.top, style='blue.TSeparator').place(relx=0, rely=0.05, relwidth=int(step) / 100)

    def sendButton_onClick(self, ev=None):
        self.on_send_show('10')
        req = self.request_to_json()
        self.on_send_show('20')
        self.responseText.delete("1.0", "end-1c")
        self.respHeaderText.delete("1.0", "end-1c")
        method = req['method']
        url = req['url']
        body = req['req']
        auth = req['auth']
        headers = req['headers']
        var_replaced = []
        if os.path.exists(OPER_DIR + VARS_FILE):
            with open(OPER_DIR + VARS_FILE, 'r') as fp:
                var_replaced = json.load(fp)
        self.on_send_show('30')
        if var_replaced:
            for item in var_replaced:
                k, v = item[0], item[1]
                print(k, v)
                rk = '$' + str(k) + '$'
                url = url.replace(rk, v)
                body = body.replace(rk, v)
        self.on_send_show('40')
        print('url:', url)
        print('body:', body)
        print('headers:', headers)
        self.on_send_show('50')
        result = re.findall(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", url)
        ip = result[0] if result else None
        cert = None
        if ip and os.path.exists(OPER_DIR + CERT_FILE):
            with open(OPER_DIR + CERT_FILE, 'r') as fp:
                js = json.load(fp)
                for item in js:
                    if item[0] == ip:
                        cert = [item[1], item[2]]
        self.on_send_show('60')
        try:
            reqMethod = getattr(requests, method)
            print('pre')
            resp = reqMethod(url, headers=headers, data=body, auth=auth, cert=cert, verify=False)
            print('after')
            self.on_send_show('80')
            print(resp.headers)
            header_text = '\n'.join([str(k) + ':' + str(v) for k, v in resp.headers.items()])
            self.respHeaderText.insert('1.0', header_text)
            if resp.ok:
                self.on_send_show('success', resp.status_code)
            else:
                self.on_send_show('fail', resp.status_code)
            try:
                self.responseText.insert('1.0', json.dumps(json.loads(resp.text), ensure_ascii=False, indent=4,
                                                           separators=(',', ':')))
            except BaseException:
                self.responseText.insert('1.0', resp.text)
        except BaseException as err:
            self.on_send_show('fail')
            self.responseText.insert('1.0', err)

    @staticmethod
    def popup4(event, *args, **kwargs):
        Popupmenu4 = tk.Menu(root, tearoff=0)
        Popupmenu4.configure(activebackground="#f9f9f9")
        Popupmenu4.configure(activeborderwidth="1")
        Popupmenu4.configure(activeforeground="black")
        Popupmenu4.configure(background="#d9d9d9")
        Popupmenu4.configure(borderwidth="1")
        Popupmenu4.configure(disabledforeground="#a3a3a3")
        Popupmenu4.configure(font="{Microsoft YaHei UI} 9")
        Popupmenu4.configure(foreground="black")
        Popupmenu4.post(event.x_root, event.y_root)

    @staticmethod
    def popup5(event, *args, **kwargs):
        Popupmenu5 = tk.Menu(root, tearoff=0)
        Popupmenu5.configure(activebackground="#f9f9f9")
        Popupmenu5.configure(activeborderwidth="1")
        Popupmenu5.configure(activeforeground="black")
        Popupmenu5.configure(background="#d9d9d9")
        Popupmenu5.configure(borderwidth="1")
        Popupmenu5.configure(disabledforeground="#a3a3a3")
        Popupmenu5.configure(font="{Microsoft YaHei UI} 9")
        Popupmenu5.configure(foreground="black")
        Popupmenu5.post(event.x_root, event.y_root)


class mainFrame:
    def __init__(self, top=None):
        """This class configures and populates the toplevel window.
           top is the toplevel containing window."""
        _bgcolor = '#fcf7f3'  # X11 color: 'gray85'
        _fgcolor = '#000000'  # X11 color: 'black'
        _compcolor = '#d9d9d9'  # X11 color: 'gray85'
        _ana1color = '#d9d9d9'  # X11 color: 'gray85'
        _ana2color = '#ececec'  # Closest X11 color: 'gray92'
        self.style = ttk.Style()
        if sys.platform == "win32":
            self.style.theme_use('winnative')
        self.style.configure('.', background=_bgcolor)
        self.style.configure('.', foreground=_fgcolor)
        self.style.configure('.', font="TkDefaultFont")
        self.style.map('.', background=[('selected', _compcolor), ('active', _ana2color)])
        self.top = top
        self.top.geometry(str(WIN_WIDTH) + 'x' + str(WIN_HEIGHT) + '+0+0')
        self.top.minsize(120, 1)
        self.top.maxsize(3844, 1041)
        self.top.resizable(1, 1)
        self.top.title("rest")
        self.top.configure(background="#fcf7f3")

        self.style.configure('Treeview', font=DEF_FONT)
        self.reqTree = ScrolledTreeView(top)
        self.reqTree.place(relx=0.006, rely=0, relheight=0.974
                           , relwidth=0.113)
        self.reqTree.configure(displaycolumns="")
        self.reqTree.heading("#0", text="items")
        self.reqTree.heading("#0", anchor="center")
        self.reqTree.column("#0", width="95")
        self.reqTree.column("#0", minwidth="20")
        self.reqTree.column("#0", stretch="1")
        self.reqTree.column("#0", anchor="w")
        # tree struct:parent and children
        self.reqTree_ids = collections.defaultdict(list)
        # tree item id and id's request
        self.request_map = {}

        self.menubar = tk.Menu(top, font=('Consolas', 12), bg=_bgcolor, fg=_fgcolor)
        top.configure(menu=self.menubar)

        self.sub_menu = tk.Menu(top, tearoff=0)
        self.menubar.add_cascade(menu=self.sub_menu,
                                 activebackground="#ececec",
                                 activeforeground="#000000",
                                 background="#fcf7f3",
                                 compound="left",
                                 foreground="#000000",
                                 font=DEF_FONT,
                                 label="file")
        self.sub_menu.add_command(
            activebackground="#ececec",
            activeforeground="#000000",
            background="#fcf7f3",
            foreground="#000000",
            font=DEF_FONT,
            label="import",
            command=self.importButton_onClick)
        self.sub_menu.add_command(
            activebackground="#ececec",
            activeforeground="#000000",
            background="#fcf7f3",
            foreground="#000000",
            font=DEF_FONT,
            label="export",
            command=self.exportButton_onClick)
        self.sub_menu.add_command(
            activebackground="#ececec",
            activeforeground="#000000",
            background="#fcf7f3",
            foreground="#000000",
            font=DEF_FONT,
            label="vars",
            command=self.varsButton_onClick)
        self.sub_menu.add_command(
            activebackground="#ececec",
            activeforeground="#000000",
            background="#fcf7f3",
            foreground="#000000",
            font=DEF_FONT,
            label="cert",
            command=self.certButton_onClick)

        global _images
        _images = (

            tk.PhotoImage("img_close", data='''R0lGODlhDAAMAIQUADIyMjc3Nzk5OT09PT
                         8/P0JCQkVFRU1NTU5OTlFRUVZWVmBgYGF hYWlpaXt7e6CgoLm5ucLCwszMzNbW
                         1v//////////////////////////////////// ///////////yH5BAEKAB8ALA
                         AAAAAMAAwAAAUt4CeOZGmaA5mSyQCIwhCUSwEIxHHW+ fkxBgPiBDwshCWHQfc5
                         KkoNUtRHpYYAADs= '''),

            tk.PhotoImage("img_closeactive", data='''R0lGODlhDAAMAIQcALwuEtIzFL46
                         INY0Fdk2FsQ8IdhAI9pAIttCJNlKLtpLL9pMMMNTP cVTPdpZQOBbQd60rN+1rf
                         Czp+zLxPbMxPLX0vHY0/fY0/rm4vvx8Pvy8fzy8P//////// ///////yH5BAEK
                         AB8ALAAAAAAMAAwAAAVHYLQQZEkukWKuxEgg1EPCcilx24NcHGYWFhx P0zANBE
                         GOhhFYGSocTsax2imDOdNtiez9JszjpEg4EAaA5jlNUEASLFICEgIAOw== '''),

            tk.PhotoImage("img_closepressed", data='''R0lGODlhDAAMAIQeAJ8nD64qELE
                         rELMsEqIyG6cyG7U1HLY2HrY3HrhBKrlCK6pGM7lD LKtHM7pKNL5MNtiViNaon
                         +GqoNSyq9WzrNyyqtuzq+O0que/t+bIwubJw+vJw+vTz+zT z////////yH5BAE
                         KAB8ALAAAAAAMAAwAAAVJIMUMZEkylGKuwzgc0kPCcgl123NcHWYW Fs6Gp2mYB
                         IRgR7MIrAwVDifjWO2WwZzpxkxyfKVCpImMGAeIgQDgVLMHikmCRUpMQgA7 ''')
        )

        self.style.element_create("close", "image", "img_close",
                                  ("active", "pressed", "!disabled", "img_closepressed"),
                                  ("active", "alternate", "!disabled",
                                   "img_closeactive"), border=8, sticky='')

        self.style.layout("ClosetabNotebook", [("ClosetabNotebook.client",
                                                {"sticky": "nswe"})])
        self.style.layout("ClosetabNotebook.Tab", [
            ("ClosetabNotebook.tab",
             {"sticky": "nswe",
              "children": [
                  ("ClosetabNotebook.padding", {
                      "side": "top",
                      "sticky": "nswe",
                      "children": [
                          ("ClosetabNotebook.focus", {
                              "side": "top",
                              "sticky": "nswe",
                              "children": [
                                  ("ClosetabNotebook.label", {"side":
                                                                  "left", "sticky": ''}),
                                  ("ClosetabNotebook.close", {"side":
                                                                  "left", "sticky": ''}), ]})]})]})])

        PNOTEBOOK = "ClosetabNotebook"

        self.style.configure('TNotebook.Tab', background=_bgcolor)
        self.style.configure('TNotebook.Tab', foreground=_fgcolor)
        self.style.map('TNotebook.Tab', background=
        [('selected', _compcolor), ('active', _ana2color)])
        self.requestNotebook = ttk.Notebook(self.top)
        self.requestNotebook.enable_traversal()
        self.requestNotebook.place(relx=0.12, rely=0, relheight=0.974, relwidth=0.875)
        self.requestNotebook.configure(takefocus="")
        self.requestNotebook.configure(style=PNOTEBOOK)
        self.notebook_list = []
        self.notebook_idi_map = {}

        self.requestNotebook.bind('<Button-1>', self.notebook_press)
        self.requestNotebook.bind('<ButtonRelease-1>', self.notebook_release)
        self.requestNotebook.bind('<Motion>', _mouse_over)
        self.reqTree.bind("<Button-3>", func=self.reqTree_onRightClick)
        self.reqTree.bind('<Double-Button-1>', func=self.reqTree_onDoubleClick)
        self.top.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.on_opening()

    def notebook_press(self, event):
        print(self.requestNotebook.place_slaves())
        widget = event.widget
        element = widget.identify(event.x, event.y)
        print('adddddd')
        if "close" in element:
            index = widget.index("@%d,%d" % (event.x, event.y))
            widget.state(['pressed'])
            widget._active = index

    def notebook_release(self, event):
        widget = event.widget
        if not widget.instate(['pressed']):
            return
        element = widget.identify(event.x, event.y)
        try:
            index = widget.index("@%d,%d" % (event.x, event.y))
        except tk.TclError:
            pass
        if "close" in element and widget._active == index:
            self.ask_and_save(index)
            widget.forget(index)
            widget.event_generate("<<NotebookTabClosed>>")

        widget.state(['!pressed'])
        widget._active = None

    def certButton_onClick(self):
        js = []
        if os.path.exists(OPER_DIR + CERT_FILE):
            with open(OPER_DIR + CERT_FILE, 'r') as fp:
                js = json.load(fp)
        dia = CertDialog('cert manager', ['ip', 'cert file', 'key file'], js)
        root.wait_window(dia)
        js = dia.get()
        with open(OPER_DIR + CERT_FILE, 'w') as fp:
            json.dump(js, fp)

    def varsButton_onClick(self):
        js = []
        if os.path.exists(OPER_DIR + VARS_FILE):
            with open(OPER_DIR + VARS_FILE, 'r') as fp:
                js = json.load(fp)
        dialog = TreeViewDialog('edit variables please', ['key', 'value'], js)
        root.wait_window(dialog)
        js = dialog.get()
        with open(OPER_DIR + VARS_FILE, 'w') as fp:
            json.dump(js, fp)

    def load_json_file(self, p):
        with open(p, 'r') as fp:
            req_s = json.load(fp)
            print(req_s)
            ids = req_s['ids']
            maps = req_s['maps']
            for k, v in ids.items():
                if k not in self.reqTree_ids.keys():
                    self.reqTree.insert('', tk.END, k, text=k)
                for item in v:
                    if item not in self.reqTree_ids.get(k, list()):
                        self.reqTree.insert(k, tk.END, item, text=item[item.index('_') + 1:])
            self.reqTree_ids.update(ids)
            self.request_map.update(maps)

    def on_opening(self):
        di = OPER_DIR + DATA_FILE
        if not os.path.exists(di):
            return
        self.load_json_file(di)
        ti = OPER_DIR + TEMP_FILE
        if os.path.exists(ti):
            with open(ti) as fp:
                js = json.load(fp)
                for k, v in js.items():
                    self.add_request_frame(k, v)

    def on_closing(self):
        print('close')
        with open(OPER_DIR + DATA_FILE, 'w') as fp:
            json.dump({'ids': self.reqTree_ids, 'maps': self.request_map}, fp)
        with open(OPER_DIR + TEMP_FILE, 'w') as fp:
            maps = dict({k: v.request_to_json() for k, v in self.notebook_idi_map.items()})
            json.dump(maps, fp)
        self.top.destroy()

    def importButton_onClick(self):
        print('open')
        name = filedialog.askopenfilename(title='open json file', filetypes=[('*', '*.json')])
        try:
            if name:
                self.load_json_file(name)
                messagebox.showinfo('info', 'import success!')
        except TypeError:
            messagebox.showerror('error', 'specified json file is invalid!')

    def exportButton_onClick(self):
        dic = {'ids': self.reqTree_ids, 'maps': self.request_map}
        name = filedialog.asksaveasfilename(title='save to', filetypes=[('*', '*.json')])
        print(name)
        if name:
            with open(name, 'w') as fp:
                json.dump(dic, fp)
        messagebox.showinfo('info', 'export success!')

    def reqTree_onDoubleClick(self, ev=None):
        selectedItem = self.reqTree.selection()
        print(selectedItem)
        if len(selectedItem) == 1 and selectedItem[0] in self.request_map.keys():
            self.reqTree_menubar_open_rest(selectedItem[0])

    def raise_menubar(self, label_funcs, position):
        menubar = tk.Menu(self.top, tearoff=False)
        menubar.delete(0, tk.END)
        for k, v in label_funcs.items():
            menubar.add_command(label=k, command=v)
            menubar.add_separator()
        menubar.delete(tk.END)
        menubar.post(*position)

    def reqTree_onRightClick(self, event):
        selectedItem = self.reqTree.selection()
        dic = {}
        if not selectedItem:
            dic = {'new collection': self.reqTree_menubar_new_collection}
        elif len(selectedItem) == 1 and selectedItem[0] in self.reqTree_ids.keys():
            dic = {
                'new collection': self.reqTree_menubar_new_collection,
                'new rest request': functools.partial(self.reqTree_menubar_new_rest, selectedItem[0]),
                'delete': functools.partial(self.reqTree_menubar_delete, selectedItem)
            }
        elif len(selectedItem) == 1 and selectedItem[0] in self.request_map.keys():
            dic = {
                'open': functools.partial(self.reqTree_menubar_open_rest, selectedItem[0]),
                'duplicate': functools.partial(self.reqTree_menubar_duplicate_rest, selectedItem[0]),
                'add basic auth': functools.partial(self.reqTree_menubar_add_basic_auth, selectedItem[0]),
                'delete': functools.partial(self.reqTree_menubar_delete, selectedItem)
            }
        elif len(selectedItem) > 1:
            dic = {'delete': functools.partial(self.reqTree_menubar_delete, selectedItem)}
        self.raise_menubar(dic, [event.x_root, event.y_root])

    def reqTree_menubar_add_basic_auth(self, item):
        auth = self.request_map[item].get('auth')
        on, op = auth if auth else ('', '')
        dialog = ObtainValueDialog('add auth', {'usernmae': on, 'password': op})
        root.wait_window(dialog)
        username, password = dialog.get().values()
        if username and password:
            self.request_map[item]['auth'] = (username, password)
            self.notebook_idi_map[item].update_data({'auth': (username, password)})
        else:
            if 'auth' in self.request_map[item].keys():
                del self.request_map[item]['auth']
            if 'auth' in self.notebook_idi_map.keys():
                self.notebook_idi_map[item].update_data({'auth': []})
        print(self.request_map)

    def reqTree_menubar_new_collection(self):
        print('coll')
        dialog = ObtainValueDialog('input collection name', {'name': None})
        self.top.wait_window(dialog)
        name = dialog.get().get('name', None)
        if name:
            self.reqTree.insert("", tk.END, name, text=name)
            self.reqTree_ids[name] = list()
        else:
            messagebox.showerror('error', 'please input a valid collection name!')

    def reqTree_menubar_new_rest(self, selectedName):
        dialog = ObtainValueDialog('input request name', {'name': None})
        root.wait_window(dialog)
        name = dialog.get().get('name', None)
        if not name:
            messagebox.showerror('error', 'please input a valid rest name!')
            return
        dic = dict({'method': 'get', 'url': '', 'params': {},
                    'headers': {},
                    'req': '', 'resp': '',
                    'respHeaders': '', 'auth': None})
        idi = selectedName + '_' + name
        self.reqTree.insert(selectedName, tk.END, idi, text=name)
        self.reqTree_ids[selectedName].append(idi)
        self.request_map[idi] = dic
        self.add_request_frame(idi, dic)
        print(self.reqTree_ids)
        print(self.request_map)

    def add_request_frame(self, idi, request):
        tab = tk.Frame(self.requestNotebook)
        reqBook = ReqNoteBook(tab, request)
        self.requestNotebook.add(tab, padding=1, text=idi[idi.index('_') + 1:] if idi.find('_') != -1 else idi)
        tab.configure(background="#fcf7f3", highlightbackground="#fcf7f3", highlightcolor="black")
        self.notebook_list.append(idi)
        self.notebook_idi_map[idi] = reqBook
        self.requestNotebook.select(self.notebook_list.index(idi))

    def reqTree_menubar_open_rest(self, item):
        if item in self.notebook_list:
            self.requestNotebook.select(self.notebook_list.index(item))
        else:
            request = self.request_map[item]
            self.add_request_frame(item, request)

    def reqTree_menubar_delete(self, selectedItems):
        rep = [item if item.find('_') == -1 else item[item.index('_') + 1:] for item in selectedItems]
        if not messagebox.askokcancel('warn', 'confirm to del reqs {}'.format(reprlib.repr(rep))):
            return
        for item in selectedItems:
            if item in self.request_map.keys():
                del self.request_map[item]
            for k, v in self.reqTree_ids.items():
                if item in v:
                    v.remove(item)
            if item in self.reqTree_ids.keys():
                del self.reqTree_ids[item]
            if self.reqTree.exists(item):
                self.reqTree.delete(item)
        rest = [item for item in selectedItems if item.find('_') != -1]
        for r in rest:
            if r in self.notebook_list:
                self.requestNotebook.forget(self.notebook_list.index(r))
                del self.notebook_idi_map[r]
        self.notebook_list = self.notebook_list - rest
        print(self.reqTree_ids)
        print(self.request_map)

    def reqTree_menubar_duplicate_rest(self, item):
        dialog = ObtainValueDialog('input new name', {'new name': None})
        root.wait_window(dialog)
        new_name = dialog.get().get('new name', None)
        if not new_name:
            messagebox.showerror('error', 'please input a valid rest name!')
            return
        parent = ''
        for k, v in self.reqTree_ids.items():
            if item in v:
                parent = k
                break
        self.reqTree.insert(parent, tk.END, parent + '_' + new_name, text=new_name)
        self.reqTree_ids[parent].append(parent + '_' + new_name)
        self.request_map[parent + '_' + new_name] = self.request_map[item]

    def ask_and_save(self, index):
        idi = self.notebook_list[index]
        js = self.notebook_idi_map[idi].request_to_json()
        old = self.request_map[idi]

        def cmp_dict(src_data, dst_data):
            if type(src_data) != type(dst_data):
                return False
            if isinstance(src_data, dict):
                for key in src_data:
                    if key not in dst_data:
                        return False
                    cmp_dict(src_data[key], dst_data[key])
            elif isinstance(src_data, list):
                for src_list, dst_list in zip(sorted(src_data), sorted(dst_data)):
                    cmp_dict(src_list, dst_list)
            else:
                return src_data == dst_data

        if not cmp_dict(js, old) and messagebox.askyesno('warn',
                                                         'save request {} or not ?'.format(idi)):
            self.request_map[idi] = js
        self.notebook_list.remove(idi)
        del self.notebook_idi_map[idi]

    @staticmethod
    def popup4(event, *args, **kwargs):
        Popupmenu4 = tk.Menu(root, tearoff=0)
        Popupmenu4.configure(activebackground="#f9f9f9")
        Popupmenu4.configure(activeborderwidth="1")
        Popupmenu4.configure(activeforeground="black")
        Popupmenu4.configure(background="#d9d9d9")
        Popupmenu4.configure(borderwidth="1")
        Popupmenu4.configure(disabledforeground="#a3a3a3")
        Popupmenu4.configure(font="{Microsoft YaHei UI} 9")
        Popupmenu4.configure(foreground="black")
        Popupmenu4.post(event.x_root, event.y_root)

    @staticmethod
    def popup5(event, *args, **kwargs):
        Popupmenu5 = tk.Menu(root, tearoff=0)
        Popupmenu5.configure(activebackground="#f9f9f9")
        Popupmenu5.configure(activeborderwidth="1")
        Popupmenu5.configure(activeforeground="black")
        Popupmenu5.configure(background="#d9d9d9")
        Popupmenu5.configure(borderwidth="1")
        Popupmenu5.configure(disabledforeground="#a3a3a3")
        Popupmenu5.configure(font="{Microsoft YaHei UI} 9")
        Popupmenu5.configure(foreground="black")
        Popupmenu5.post(event.x_root, event.y_root)


# The following code is added to facilitate the Scrolled widgets you specified.
class AutoScroll(object):
    '''Configure the scrollbars for a widget.'''

    def __init__(self, master):
        #  Rozen. Added the try-except clauses so that this class
        #  could be used for scrolled entry widget for which vertical
        #  scrolling is not supported. 5/7/14.
        try:
            vsb = ttk.Scrollbar(master, orient='vertical', command=self.yview)
        except:
            pass
        hsb = ttk.Scrollbar(master, orient='horizontal', command=self.xview)

        # self.configure(yscrollcommand=_autoscroll(vsb),
        #    xscrollcommand=_autoscroll(hsb))
        try:
            self.configure(yscrollcommand=self._autoscroll(vsb))
        except:
            pass
        self.configure(xscrollcommand=self._autoscroll(hsb))

        self.grid(column=0, row=0, sticky='nsew')
        try:
            vsb.grid(column=1, row=0, sticky='ns')
        except:
            pass
        hsb.grid(column=0, row=1, sticky='ew')

        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Copy geometry methods of master  (taken from ScrolledText.py)
        if py3:
            methods = tk.Pack.__dict__.keys() | tk.Grid.__dict__.keys() \
                      | tk.Place.__dict__.keys()
        else:
            methods = tk.Pack.__dict__.keys() + tk.Grid.__dict__.keys() \
                      + tk.Place.__dict__.keys()

        for meth in methods:
            if meth[0] != '_' and meth not in ('config', 'configure'):
                setattr(self, meth, getattr(master, meth))

    @staticmethod
    def _autoscroll(sbar):
        '''Hide and show scrollbar as needed.'''

        def wrapped(first, last):
            first, last = float(first), float(last)
            if first <= 0 and last >= 1:
                sbar.grid_remove()
            else:
                sbar.grid()
            sbar.set(first, last)

        return wrapped

    def __str__(self):
        return str(self.master)


def _create_container(func):
    '''Creates a ttk Frame with a given master, and use this new frame to
    place the scrollbars and the widget.'''

    def wrapped(cls, master, **kw):
        container = ttk.Frame(master)
        container.bind('<Enter>', lambda e: _bound_to_mousewheel(e, container))
        container.bind('<Leave>', lambda e: _unbound_to_mousewheel(e, container))
        return func(cls, container, **kw)

    return wrapped


class ScrolledText(AutoScroll, tk.Text):
    '''A standard Tkinter Text widget with scrollbars that will
    automatically show/hide as needed.'''

    @_create_container
    def __init__(self, master, **kw):
        tk.Text.__init__(self, master, **kw)
        AutoScroll.__init__(self, master)


class ScrolledListBox(AutoScroll, tk.Listbox):
    '''A standard Tkinter Listbox widget with scrollbars that will
    automatically show/hide as needed.'''

    @_create_container
    def __init__(self, master, **kw):
        tk.Listbox.__init__(self, master, **kw)
        AutoScroll.__init__(self, master)

    def size_(self):
        sz = tk.Listbox.size(self)
        return sz


class ScrolledTreeView(AutoScroll, ttk.Treeview):
    '''A standard ttk Treeview widget with scrollbars that will
    automatically show/hide as needed.'''

    @_create_container
    def __init__(self, master, **kw):
        ttk.Treeview.__init__(self, master, **kw)
        AutoScroll.__init__(self, master)


import platform


def _bound_to_mousewheel(event, widget):
    child = widget.winfo_children()[0]
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        child.bind_all('<MouseWheel>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Shift-MouseWheel>', lambda e: _on_shiftmouse(e, child))
    else:
        child.bind_all('<Button-4>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Button-5>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Shift-Button-4>', lambda e: _on_shiftmouse(e, child))
        child.bind_all('<Shift-Button-5>', lambda e: _on_shiftmouse(e, child))


def _unbound_to_mousewheel(event, widget):
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        widget.unbind_all('<MouseWheel>')
        widget.unbind_all('<Shift-MouseWheel>')
    else:
        widget.unbind_all('<Button-4>')
        widget.unbind_all('<Button-5>')
        widget.unbind_all('<Shift-Button-4>')
        widget.unbind_all('<Shift-Button-5>')


def _on_mousewheel(event, widget):
    if platform.system() == 'Windows':
        widget.yview_scroll(-1 * int(event.delta / 120), 'units')
    elif platform.system() == 'Darwin':
        widget.yview_scroll(-1 * int(event.delta), 'units')
    else:
        if event.num == 4:
            widget.yview_scroll(-1, 'units')
        elif event.num == 5:
            widget.yview_scroll(1, 'units')


def _on_shiftmouse(event, widget):
    if platform.system() == 'Windows':
        widget.xview_scroll(-1 * int(event.delta / 120), 'units')
    elif platform.system() == 'Darwin':
        widget.xview_scroll(-1 * int(event.delta), 'units')
    else:
        if event.num == 4:
            widget.xview_scroll(-1, 'units')
        elif event.num == 5:
            widget.xview_scroll(1, 'units')


# The following code is add to handle mouse events with the close icons
# in PNotebooks widgets.


def _mouse_over(event):
    widget = event.widget
    element = widget.identify(event.x, event.y)
    if "close" in element:
        widget.state(['alternate'])
    else:
        widget.state(['!alternate'])


if __name__ == '__main__':
    vp_start_gui()
