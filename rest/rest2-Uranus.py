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
import reprlib
import sys

import requests
from requests.auth import HTTPBasicAuth

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

OPER_DIR = 'C:\\restdata\\'
VARS_FILE = 'vars.json'
CERT_FILE = 'cert.json'
DATA_FILE = 'data.json'

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


class VarsDialog(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.title('edit variables please')
        x = root.winfo_x() + 450
        y = root.winfo_y() + 200
        self.geometry('600x400+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)

        row1 = ttk.Frame(self)
        row1.pack(fill='x')
        self.varsText = ScrolledText(row1)
        self.varsText.pack(fill='x')
        self.varsText.configure(font=('Consolas', 10))
        self.varsText.focus_set()

        row2 = ttk.Frame(self)
        row2.pack(fill="x")
        ttk.Button(row2, text="cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(row2, text="confirm", command=self.ok).pack(side=tk.RIGHT)
        if os.path.exists(OPER_DIR + VARS_FILE):
            with open(OPER_DIR + VARS_FILE) as fp:
                s = json.load(fp)
                display = '\n'.join([k + ':' + v for k, v in s.items()])
                self.varsText.insert('1.0', display)

    def ok(self):
        with open(OPER_DIR + VARS_FILE, 'w') as fp:
            text = self.varsText.get("1.0", "end-1c").replace('\r\n', '\n').split('\n')
            if text:
                kv = dict(item.strip().split(':') for item in text if item)
                print(kv)
                json.dump(kv, fp)
        self.destroy()  # 销毁窗口

    def cancel(self):
        self.destroy()


class InputDialog(tk.Toplevel):
    def __init__(self, title):
        super().__init__()
        self.title(title)
        x = root.winfo_x() + 200
        y = root.winfo_y() + 300
        self.geometry('230x30+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)
        # 第一行（两列）
        row1 = ttk.Frame(self)
        row1.pack(fill="x")
        self.name = tk.StringVar()
        entry = ttk.Entry(row1, textvariable=self.name, width=20)
        entry.configure(font=DEF_FONT)
        entry.pack(side=tk.LEFT)
        entry.focus_set()
        entry.bind('<Return>', self.ok)
        ttk.Button(row1, text="confirm", command=self.ok).pack(side=tk.RIGHT)
        self.value = ''

    def ok(self, ev=None):
        self.value = self.name.get()
        self.destroy()

    def cancel(self):
        self.destroy()


class UnsavedReqDialog(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.title('save req')
        x = root.winfo_x() + 700
        y = root.winfo_y() + 200
        self.geometry('240x80+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)

        row1 = ttk.Frame(self)
        row1.pack(fill="x")
        ttk.Label(row1, text='collection name：', width=15).pack(side=tk.LEFT)
        self.cName = tk.StringVar()
        entry = ttk.Entry(row1, textvariable=self.cName, width=20)
        entry.focus_set()
        entry.pack(side=tk.LEFT)

        # 第二行
        row2 = ttk.Frame(self)
        row2.pack(fill="x", ipadx=1, ipady=1)
        ttk.Label(row2, text='request name：', width=15).pack(side=tk.LEFT)
        self.rName = tk.StringVar()
        ttk.Entry(row2, textvariable=self.rName, width=20).pack(side=tk.LEFT)

        # 第三行
        row3 = ttk.Frame(self)
        row3.pack(fill="x")
        ttk.Button(row3, text="cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(row3, text='confirm', command=self.ok).pack(side=tk.RIGHT)

    def names(self):
        return self.cName.get(), self.rName.get()

    def ok(self, ev=None):
        self.destroy()

    def cancel(self):
        self.destroy()


class AddBasicAuthDialog(tk.Toplevel):
    def __init__(self, ou, op):
        super().__init__()
        self.title('save req')
        x = root.winfo_x() + 400
        y = root.winfo_y() + 300
        self.geometry('220x80+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)

        row1 = ttk.Frame(self)
        row1.pack(fill="x")
        ttk.Label(row1, text='username：', width=15).pack(side=tk.LEFT)
        self.username = tk.StringVar()
        entry = ttk.Entry(row1, textvariable=self.username, width=20)
        entry.insert(0, ou)
        entry.focus_set()
        entry.pack(side=tk.LEFT)

        # 第二行
        row2 = ttk.Frame(self)
        row2.pack(fill="x", ipadx=1, ipady=1)
        ttk.Label(row2, text='password：', width=15).pack(side=tk.LEFT)
        self.password = tk.StringVar()
        en = ttk.Entry(row2, textvariable=self.password, show='*', width=20)
        en.insert(0, op)
        en.pack(side=tk.LEFT)

        # 第三行
        row3 = ttk.Frame(self)
        row3.pack(fill="x")
        ttk.Button(row3, text="cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(row3, text='confirm', command=self.ok).pack(side=tk.RIGHT)

    def names(self):
        return self.username.get(), self.password.get()

    def ok(self, ev=None):
        self.destroy()

    def cancel(self):
        self.destroy()


class AddCertItemDialog(tk.Toplevel):
    def __init__(self, top):
        super().__init__()
        self.title('input cert values')
        x = top.winfo_x() + 100
        y = top.winfo_y() + 100
        self.geometry('300x110+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)

        row1 = ttk.Frame(self)
        row1.pack(fill="x")
        ttk.Label(row1, text='ip：', width=15).pack(side=tk.LEFT)
        self.ipVar = tk.StringVar()
        entry = ttk.Entry(row1, textvariable=self.ipVar, width=20)
        entry.focus_set()
        entry.pack(side=tk.LEFT)

        # 第二行
        row2 = ttk.Frame(self)
        row2.pack(fill="x", ipadx=1, ipady=1)
        ttk.Label(row2, text='cert file：', width=15).pack(side=tk.LEFT)
        self.certButton = ttk.Label(row2, text='   ...', width=40)
        self.certButton.pack(side=tk.LEFT)
        self.certButton.bind('<Button-1>', func=self.get_cert)

        row3 = ttk.Frame(self)
        row3.pack(fill="x", ipadx=1, ipady=1)
        ttk.Label(row3, text='key file：', width=15).pack(side=tk.LEFT)
        self.keyButton = ttk.Label(row3, text='   ...', width=40)
        self.keyButton.pack(side=tk.LEFT)
        self.keyButton.bind('<Button-1>', func=self.get_key)

        # 第三行
        row4 = ttk.Frame(self)
        row4.pack(fill="x")
        ttk.Button(row4, text="cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(row4, text='ok', command=self.ok).pack(side=tk.RIGHT)

        self.ip, self.cert, self.key = '', '', ''

    def get_cert(self, ev=None):
        name = filedialog.askopenfilename(title='select the cert file', filetypes=[('*', '*.cert')])
        if name:
            self.cert = name
            self.certButton.configure(text=name)

    def get_key(self, ev=None):
        name = filedialog.askopenfilename(title='select the key file', filetypes=[('*', '*.key')])
        if name:
            self.key = name
            self.keyButton.configure(text=name)

    def values(self):
        return self.ip, self.cert, self.key

    def ok(self, ev=None):
        self.ip = self.ipVar.get()
        self.destroy()

    def cancel(self):
        self.destroy()


class CertManageDialog(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.title('cert edit')
        x = root.winfo_x() + 1000
        y = root.winfo_y() + 200
        self.geometry('500x400+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)
        # 第一行（两列）
        self.certListBox = ScrolledListBox(self)
        self.certListBox.place(relx=0.01, rely=0.01, relheight=0.90, relwidth=0.95)
        self.certListBox.configure(font=('Consolas', 12))
        self.certListBox.focus_set()
        self.certListBox.bind('<Button-3>', func=self.display_cert_menu)
        self.insert_exist_certs()

        self.closeButton = ttk.Button(self)
        self.closeButton.configure(takefocus="", text='''close''', command=self.close)
        self.closeButton.place(relx=0.85, rely=0.92, height=27, width=57)

    def display_cert_menu(self, event):
        print(self.certListBox.curselection())
        items = self.certListBox.curselection()
        menubar = tk.Menu(self, tearoff=False)
        menubar.delete(0, tk.END)
        menubar.add_command(label='new cert', command=self.and_cert_item)
        if items:
            menubar.add_separator()
            menubar.add_command(label='delete', command=lambda: self.certListBox.delete(items[0]))
        menubar.post(event.x_root, event.y_root)

    def and_cert_item(self):
        dialog = AddCertItemDialog(self)
        self.wait_window(dialog)
        ip, cert, key = dialog.values()
        print(dialog.values())
        if not ip or not cert or not key:
            return
        item = ' | '.join([ip, cert, key])
        self.certListBox.insert(0, item)

    def close(self):
        items = self.certListBox.get(0, tk.END)
        js = {}
        for item in items:
            ip, cert, key = item.split(' | ')
            js[ip] = (ip, cert, key)
        with open(OPER_DIR + CERT_FILE, 'w') as fp:
            json.dump(js, fp)
        self.destroy()

    def insert_exist_certs(self):
        if os.path.exists(OPER_DIR + CERT_FILE):
            with open(OPER_DIR + CERT_FILE, 'r') as fp:
                js = json.load(fp)
                for item in js.values():
                    self.certListBox.insert(0, ' | '.join(item))


class TemplateDialog(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.title('input name please')
        x = root.winfo_x() + 400
        y = root.winfo_y() + 300
        self.geometry('200x100+' + str(x) + '+' + str(y))
        self.attributes("-toolwindow", 1)
        self.wm_attributes("-topmost", 1)
        # 第一行（两列）
        row1 = tk.Frame(self)
        row1.pack(fill="x")
        tk.Label(row1, text='姓名：', width=8).pack(side=tk.LEFT)
        self.name = tk.StringVar()
        tk.Entry(row1, textvariable=self.name, width=20).pack(side=tk.LEFT)

        # 第二行
        row2 = tk.Frame(self)
        row2.pack(fill="x", ipadx=1, ipady=1)
        tk.Label(row2, text='年龄：', width=8).pack(side=tk.LEFT)
        self.age = tk.IntVar()
        tk.Entry(row2, textvariable=self.age, width=20).pack(side=tk.LEFT)

        # 第三行
        row3 = tk.Frame(self)
        row3.pack(fill="x")
        tk.Button(row3, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        tk.Button(row3, text="确定", command=self.ok).pack(side=tk.RIGHT)

    def ok(self):
        self.userinfo = [self.name.get(), self.age.get()]  # 设置数据
        self.destroy()  # 销毁窗口

    def cancel(self):
        self.userinfo = None  # 空！
        self.destroy()


class mainFrame:
    def __init__(self, top=None):
        """This class configures and populates the toplevel window.
           top is the toplevel containing window."""
        _bgcolor = '#d9d9d9'  # X11 color: 'gray85'
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

        self.methodCombobox = ttk.Combobox(top)
        self.methodCombobox.place(relx=0.126, rely=0.013, relheight=0.024
                                  , relwidth=0.038)
        self.method_list = ['get', 'post', 'delete', 'patch', 'put']
        self.methodCombobox.configure(values=self.method_list, takefocus="", cursor="fleur", font=DEF_FONT,
                                      state="readonly")
        s = ttk.Style()
        s.configure('blue.TSeparator', background='blue')
        s.configure('green.TSeparator', background='green')
        s.configure('red.TSeparator', background='red')
        ttk.Separator(top).place(relx=0.124, rely=0.084, relwidth=0.918)

        self.urlEntry = ttk.Entry(top)
        self.urlEntry.place(relx=0.167, rely=0.013, relheight=0.025
                            , relwidth=0.781)
        self.urlEntry.configure(takefocus="", cursor="ibeam", font=DEF_FONT)

        self.sendButton = ttk.Button(top)
        self.sendButton.place(relx=0.958, rely=0.013, height=27, width=57)
        self.sendButton.configure(takefocus="", text='''send''')

        self.headersLabel = ttk.Label(top)
        self.headersLabel.place(relx=0.541, rely=0.05, height=21, width=54)
        self.headersLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                    text='''headers:''')

        self.headersEntry = ttk.Entry(top)
        self.headersEntry.place(relx=0.578, rely=0.05, relheight=0.024
                                , relwidth=0.37)
        self.headersEntry.configure(takefocus="", cursor="ibeam", font=DEF_FONT)

        self.paramsEntry = ttk.Entry(top)
        self.paramsEntry.place(relx=0.177, rely=0.05, relheight=0.024
                               , relwidth=0.354)
        self.paramsEntry.configure(takefocus="", cursor="ibeam", font=DEF_FONT)

        self.paramsLabel = ttk.Label(top)
        self.paramsLabel.place(relx=0.133, rely=0.05, height=21, width=51)
        self.paramsLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                   text='''params:''')

        self.requestText = ScrolledText(top)
        self.requestText.place(relx=0.124, rely=0.116, relheight=0.878
                               , relwidth=0.427)
        self.requestText.configure(background="white", font=DEF_FONT, foreground="black",
                                   highlightbackground="#d9d9d9", highlightcolor="black", insertbackground="black",
                                   insertborderwidth="3", selectbackground="#c4c4c4", selectforeground="black",
                                   wrap="none")

        self.responseText = ScrolledText(top)
        self.responseText.place(relx=0.563, rely=0.207, relheight=0.783
                                , relwidth=0.427)
        self.responseText.configure(background="white", font=DEF_FONT, foreground="black",
                                    highlightbackground="#d9d9d9", highlightcolor="black", insertbackground="black",
                                    insertborderwidth="3", selectbackground="#c4c4c4", selectforeground="black",
                                    wrap="none")

        self.reqLabel = ttk.Label(top)
        self.reqLabel.place(relx=0.13, rely=0.09, height=21, width=60)
        self.reqLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                text='''request''')

        self.respLabel = ttk.Label(top)
        self.respLabel.place(relx=0.57, rely=0.09, height=21, width=60)
        self.respLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                 text='''response''')
        self.respCodeLabel = ttk.Label(top)
        self.respCodeLabel.place(relx=0.65, rely=0.09, height=21, width=60)
        self.respCodeLabel.configure(background="#fcf7f3", foreground="#000000", font=DEF_FONT, relief="flat",
                                     text='''--''')

        self.respHeaderText = ScrolledText(top)
        self.respHeaderText.place(relx=0.562, rely=0.116, relheight=0.079
                                  , relwidth=0.427)
        self.respHeaderText.configure(background="white", font=DEF_FONT, foreground="black",
                                      highlightbackground="#d9d9d9", highlightcolor="black", insertbackground="black",
                                      insertborderwidth="3", selectbackground="#c4c4c4", selectforeground="black",
                                      wrap="none")

        self.style.configure('Treeview', font=DEF_FONT)
        self.reqTree = ScrolledTreeView(top)
        self.reqTree.place(relx=0.006, rely=0.048, relheight=0.943
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
        self.current_request = None

        self.certButton = ttk.Button(top)
        self.certButton.place(relx=0.958, rely=0.047, height=27, width=57)
        self.certButton.configure(takefocus="", text='''cert''')

        self.varsButton = ttk.Button(top)
        self.varsButton.place(relx=0.006, rely=0.014, height=27, width=60)
        self.varsButton.configure(takefocus="", text='''vars''')

        self.importButton = ttk.Button(top)
        self.importButton.place(relx=0.043, rely=0.014, height=27, width=60)
        self.importButton.configure(takefocus="", text='''import''')

        self.exportButton = ttk.Button(top)
        self.exportButton.place(relx=0.08, rely=0.014, height=27, width=60)
        self.exportButton.configure(takefocus="", text='''export''')

        self.TSeparator1 = ttk.Separator(top)
        self.TSeparator1.place(relx=0.121, rely=0.0, relheight=0.999)
        self.TSeparator1.configure(orient="vertical")
        self.binding_event()

    def binding_event(self):
        try:
            self.on_opening()
            self.methodCombobox.current(0)
            self.urlEntry.insert(0, 'http/https...')
            self.sendButton.configure(command=self.sendButton_onLeftClick)
            self.headersEntry.insert(0, 'Content-Type:application/json')
            self.reqTree.bind("<Button-3>", func=self.reqTree_onRightClick)
            self.reqTree.bind('<Double-Button-1>', func=self.reqTree_onDoubleClick)
            self.varsButton.configure(command=lambda: root.wait_window(VarsDialog()))
            self.certButton.configure(command=self.certButton_onClick)
            self.importButton.configure(command=self.importButton_onClick)
            self.exportButton.configure(command=self.exportButton_onClick)
            self.top.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.top.bind('<Control-s>', func=self.save_current_request)
            for i in vars(self):
                if i.endswith('Entry') or i.endswith('Text'):
                    attr = getattr(self, i)
                    attr.bind('<Key>', func=self.request_content_changed)
        except BaseException as e:
            messagebox.showerror('error', 'fatal error occurs:' + str(e))

    def certButton_onClick(self):
        dia = CertManageDialog()
        root.wait_window(dia)

    def request_content_changed(self, event=None):
        old = self.top.title()
        if not old.endswith('*'):
            self.top.title(old + "*")
        print('change')

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

    def on_closing(self):
        print('close')
        self.checkCurrentReqExist_and_askToSave()
        with open(OPER_DIR + DATA_FILE, 'w') as fp:
            json.dump({'ids': self.reqTree_ids, 'maps': self.request_map}, fp)
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

    def save_current_request(self, ev=None):
        if self.current_request:
            self.request_map[self.current_request].update(self.request_to_json())
        else:
            dia = UnsavedReqDialog()
            root.wait_window(dia)
            cName, rName = dia.names()
            if not cName or not rName:
                return
            if cName not in self.reqTree_ids.keys():
                self.reqTree.insert('', tk.END, cName, text=cName)
            item = cName + '_' + rName
            self.reqTree.insert(cName, tk.END, item, text=rName)
            self.reqTree_ids[cName].append(item)
            self.request_map[item] = self.request_to_json()
            self.current_request = item
            self.top.title(rName)
        tit = self.top.title()
        if tit.endswith('*'):
            self.top.title(tit[:tit.index('*')])

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
        on, op = self.request_map[item].get('auth', ('', ''))
        dialog = AddBasicAuthDialog(on, op)
        root.wait_window(dialog)
        username, password = dialog.names()
        if username and password:
            self.request_map[item]['auth'] = (username, password)
        else:
            if 'auth' in self.request_map[item].keys():
                del self.request_map[item]['auth']
        print(self.request_map)

    def reqTree_menubar_new_collection(self):
        dialog = InputDialog('input collection name')
        root.wait_window(dialog)
        print(dialog.value)
        name = dialog.value
        if name:
            self.reqTree.insert("", tk.END, name, text=name)
            self.reqTree_ids[name] = list()
        else:
            messagebox.showerror('error', 'please input a valid collection name!')

    def reqTree_menubar_new_rest(self, selectedName):
        self.checkCurrentReqExist_and_askToSave()
        dialog = InputDialog('input request name')
        root.wait_window(dialog)
        print(dialog.value)
        name = dialog.value
        if not name:
            messagebox.showerror('error', 'please input a valid rest name!')
            return
        dic = dict({'method': 'get', 'url': '', 'params': {},
                    'headers': {},
                    'req': '', 'resp': '',
                    'respHeaders': ''})
        idi = selectedName + '_' + name
        self.reqTree.insert(selectedName, tk.END, idi, text=name)
        self.reqTree_ids[selectedName].append(idi)
        self.request_map[idi] = dic
        self.top.title(name)
        self.display_request(dic)
        self.current_request = idi
        print(self.reqTree_ids)
        print(self.request_map)

    def reqTree_menubar_open_rest(self, item):
        if self.current_request == item:
            return
        self.checkCurrentReqExist_and_askToSave()
        request = self.request_map[item]
        self.top.title(item[item.index('_') + 1:])
        self.display_request(request)
        self.current_request = item
        self.respHeaderText.configure(fg='black')

    def reqTree_menubar_delete(self, selectedItems):
        if not messagebox.askokcancel('warn', 'confirm to del reqs {}'.format(reprlib.repr(list(selectedItems)))):
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
        print(self.reqTree_ids)
        print(self.request_map)

    def reqTree_menubar_duplicate_rest(self, item):
        dialog = InputDialog('input new name')
        root.wait_window(dialog)
        print(dialog.value)
        new_name = dialog.value
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

    def checkCurrentReqExist_and_askToSave(self):
        if self.top.title().endswith('*') and messagebox.askyesno('warn', 'save request {} or not ?'.format(
                self.top.title()[:self.top.title().index('*')])):
            self.save_current_request()

    def display_request(self, req):
        self.methodCombobox.set(req['method'])
        self.urlEntry.delete("0", len(self.urlEntry.get()))
        self.urlEntry.insert(0, req['url'])
        self.paramsEntry.delete('0', len(self.paramsEntry.get()))
        self.paramsEntry.insert(0, ';'.join([key + ':' + value for key, value in req['params'].items()]))
        self.headersEntry.delete('0', len(self.headersEntry.get()))
        self.headersEntry.insert(0, ';'.join([key + ':' + value for key, value in req['headers'].items()]))
        self.requestText.delete("1.0", "end-1c")
        self.requestText.insert('1.0', req['req'])
        self.respCodeLabel = ttk.Label(self.top)
        self.respCodeLabel.place(relx=0.65, rely=0.09, height=21, width=60)
        self.respCodeLabel.configure(background="#fcf7f3", foreground="black", font=DEF_FONT, relief="flat",
                                     text=req.get('respCode', '--'))
        ttk.Separator(self.top).place(relx=0.124, rely=0.084, relwidth=9.318)
        self.respHeaderText.delete("1.0", "end-1c")
        self.respHeaderText.insert('1.0', req['respHeaders'])
        self.responseText.delete("1.0", "end-1c")
        self.responseText.insert('1.0', req['resp'])

    def request_to_json(self):
        params = self.paramsEntry.get().strip()
        param_dic = {}
        header_dic = {}
        if params:
            param_dic = dict((s.split(':')[0], s.split(':')[1]) for s in list(params.split(';')))
        headers = self.headersEntry.get().strip()
        if headers:
            header_dic = dict((s.split(':')[0], s.split(':')[1]) for s in list(headers.split(';')))
        dic = {'method': self.methodCombobox.get(), 'url': self.urlEntry.get(), 'params': param_dic,
               'headers': header_dic,
               'req': self.requestText.get("1.0", "end-1c"), 'resp': self.responseText.get("1.0", "end-1c"),
               'respHeaders': self.respHeaderText.get("1.0", "end-1c"), 'respCode': self.respCodeLabel.cget('text')}
        print(dic)
        return dic

    def sendButton_onLeftClick(self):
        ttk.Separator(self.top, style='blue.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.118)
        req = self.request_to_json()
        ttk.Separator(self.top, style='blue.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.218)
        self.responseText.delete("1.0", "end-1c")
        self.respHeaderText.delete("1.0", "end-1c")
        method = req['method']
        url = req['url']
        params = req['params']
        headers = req['headers']
        body = req['req']

        var_replaced = {}
        if os.path.exists(OPER_DIR + VARS_FILE):
            with open(OPER_DIR + VARS_FILE, 'r') as fp:
                var_replaced = json.load(fp)
        if var_replaced:
            for k, v in var_replaced.items():
                rk = '$' + str(k) + '$'
                url = url.replace(rk, v)
                body = body.replace(rk, v)
                for i, j in params.items():
                    if rk in i:
                        i = i.replace(rk, v)
                    if rk in j:
                        j = j.replace(rk, v)
                    params.update({i: j})
                for i, j in headers.items():
                    if rk in i:
                        i = i.replace(rk, v)
                    if rk in j:
                        j = j.replace(rk, v)
                    headers.update({i: j})
        ttk.Separator(self.top, style='blue.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.418)
        print('url:', url)
        print('headers', headers)
        print('params', params)
        print('body', body)
        reqMethod = getattr(requests, method)
        ttk.Separator(self.top, style='blue.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.518)
        try:
            if self.current_request and self.request_map[self.current_request].get('auth', None):
                resp = reqMethod(url, params=params, headers=headers, data=body,
                                 auth=HTTPBasicAuth(*self.request_map[self.current_request]['auth']), verify=False)
            else:
                resp = reqMethod(url, params=params, headers=headers, data=body, verify=False)
            ttk.Separator(self.top, style='blue.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.718)
            print(resp)
            header_text = '\n'.join([str(k) + ':' + str(v) for k, v in resp.headers.items()])
            self.respHeaderText.insert('1.0', header_text)
            self.respCodeLabel = ttk.Label(self.top)
            self.respCodeLabel.place(relx=0.65, rely=0.09, height=21, width=60)
            if resp.ok:
                ttk.Separator(self.top, style='green.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.918)
                self.respCodeLabel.configure(background="#fcf7f3", foreground="green", font=DEF_FONT, relief="flat",
                                             text=str(resp.status_code))
                self.respHeaderText.configure(fg='green')
            else:
                ttk.Separator(self.top, style='red.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.918)
                self.respCodeLabel.configure(background="#fcf7f3", foreground="red", font=DEF_FONT, relief="flat",
                                             text=str(resp.status_code))
                self.respHeaderText.configure(fg='red')
            try:
                self.responseText.insert('1.0', json.dumps(json.loads(resp.text), indent=4, separators=(',', ':')))
            except BaseException:
                self.responseText.insert('1.0', resp.text)
        except BaseException as err:
            ttk.Separator(self.top, style='red.TSeparator').place(relx=0.124, rely=0.084, relwidth=0.918)
            self.responseText.insert('1.0', err)
        finally:
            self.request_content_changed()

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


if __name__ == '__main__':
    vp_start_gui()
