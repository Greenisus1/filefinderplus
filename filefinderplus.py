#!/usr/bin/env python3
"""FileFinder+: reusable file browser, bounded text editor, explicit shell runner."""
import os
from pathlib import Path
import stat
import subprocess
import threading
import queue

VERSION = '1.0.1'
MAX_TEXT = 2 * 1024 * 1024
TEXT_SUFFIXES = {'.txt', '.md', '.py', '.sh', '.json', '.csv', '.ini', '.cfg', '.conf', '.log', '.yaml', '.yml', '.toml', '.html', '.css', '.js', '.xml'}


def read_text(path):
    p = Path(path)
    if p.is_symlink() or not stat.S_ISREG(p.stat().st_mode):
        raise ValueError('Editing requires a regular non-symlink file.')
    with p.open('rb') as f:
        data = f.read(MAX_TEXT + 1)
    if len(data) > MAX_TEXT or b'\0' in data:
        raise ValueError('Only UTF-8 text up to 2 MiB, without NUL bytes, can be edited.')
    text = data.decode('utf-8')
    return text, data


def save_text(path, text, original=None, allow_new=False):
    """No symlinks; existing files require exact reviewed original bytes."""
    p = Path(path)
    data = text.encode('utf-8')
    if len(data) > MAX_TEXT or b'\0' in data:
        raise ValueError('Text must be at most 2 MiB and contain no NUL bytes.')
    if p.is_symlink():
        raise ValueError('Refusing to save through a symlink.')
    if p.exists():
        current, raw = read_text(p)
        if original is None or raw != original:
            raise ValueError('File changed since it was opened. Reload before saving.')
        # In-place preserves permissions; close other writers. This is not an atomic snapshot.
        with p.open('r+b') as f:
            if f.read(MAX_TEXT + 1) != original:
                raise ValueError('File changed before save.')
            f.seek(0); f.write(data); f.truncate()
    elif allow_new:
        with p.open('xb') as f:
            f.write(data)
    else:
        raise ValueError('File no longer exists. Use Save as.')
    return data


def shell_command(path):
    p = Path(path).absolute()
    if p.is_symlink() or p.suffix.lower() != '.sh' or not stat.S_ISREG(p.stat().st_mode):
        raise ValueError('Choose a regular non-symlink .sh file.')
    return ['bash', str(p)], str(p.parent)


def list_directory(path):
    p = Path(path).expanduser().resolve(strict=True)
    if not p.is_dir():
        raise ValueError('Not a folder.')
    result = []
    for child in p.iterdir():
        try:
            kind = 'Link' if child.is_symlink() else ('Folder' if child.is_dir() else 'File')
            size = '' if kind == 'Folder' else str(child.lstat().st_size)
        except OSError:
            kind, size = 'Unavailable', '?'
        result.append((child.name, kind, size))
    return p, sorted(result, key=lambda x: (x[1] != 'Folder', x[0].casefold()))


def _tk():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    return tk, ttk, messagebox, filedialog


class BrowserFrame:
    """Embeddable widget. .frame is the ttk widget; selected_paths() returns Paths.

    select_only disables editing and shell execution for an upload picker.
    selection_callback receives a tuple of paths after a selection changes.
    """
    def __init__(self, parent, start=None, select_only=False, selection_callback=None):
        self.tk, self.ttk, self.mb, self.fd = _tk()
        tk, ttk = self.tk, self.ttk
        self.select_only = select_only
        self.selection_callback = selection_callback
        self.directory = Path(start or Path.home()).expanduser().resolve()
        self.open_path = None
        self.original = None
        self.loaded_text = None
        self.process = None
        self.events = queue.Queue()
        self.frame = ttk.Frame(parent, padding=12)
        self.frame.columnconfigure(0, weight=1); self.frame.rowconfigure(2, weight=1)
        nav = ttk.Frame(self.frame); nav.grid(row=0, column=0, sticky='ew')
        ttk.Button(nav, text='Up', command=lambda: self.navigate(self.directory.parent)).pack(side='left')
        ttk.Button(nav, text='Home', command=lambda: self.navigate(Path.home())).pack(side='left', padx=6)
        self.path_var = tk.StringVar(value=str(self.directory))
        self.path_entry = ttk.Entry(nav, textvariable=self.path_var)
        self.path_entry.pack(side='left', fill='x', expand=True)
        self.path_entry.bind('<Return>', lambda e: self.navigate(self.path_var.get()))
        ttk.Button(nav, text='Open folder', command=self.choose_folder).pack(side='left', padx=6)
        ttk.Button(nav, text='Refresh', command=lambda: self.navigate(self.directory)).pack(side='left')
        self.status = tk.StringVar(value='Double-click a folder to open it. Hidden files are shown. Links are labelled.')
        ttk.Label(self.frame, textvariable=self.status, wraplength=980).grid(row=1, column=0, sticky='w', pady=(8,8))
        pane = ttk.Panedwindow(self.frame, orient='horizontal'); pane.grid(row=2, column=0, sticky='nsew')
        left = ttk.Frame(pane); left.rowconfigure(0, weight=1); left.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(left, columns=('kind','size'), show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='Name'); self.tree.heading('kind', text='Type'); self.tree.heading('size', text='Bytes')
        self.tree.column('#0', width=260); self.tree.column('kind', width=70); self.tree.column('size', width=80)
        self.tree.grid(row=0, column=0, sticky='nsew')
        sb = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview); sb.grid(row=0, column=1, sticky='ns'); self.tree.configure(yscrollcommand=sb.set)
        pane.add(left, weight=2)
        self.tree.bind('<Double-1>', self.open_selected)
        self.tree.bind('<<TreeviewSelect>>', self.selection_changed)
        if not select_only:
            right = ttk.Frame(pane); right.rowconfigure(2, weight=1); right.columnconfigure(0, weight=1)
            self.editor_title = tk.StringVar(value='Select a text file, then Open text')
            ttk.Label(right, textvariable=self.editor_title, wraplength=500).grid(row=0,column=0,sticky='w',pady=(0,8))
            bar = ttk.Frame(right); bar.grid(row=1,column=0,sticky='ew',pady=(0,8))
            for title,cmd in [('Open text',self.open_text),('Save',self.save),('Save as',self.save_as),('Run .sh',self.run_shell),('Stop',self.stop_shell)]:
                ttk.Button(bar,text=title,command=cmd).pack(side='left',padx=2)
            self.editor = tk.Text(right, wrap='none', undo=True, font=('DejaVu Sans Mono',10), background='#ffffff', foreground='#251f21')
            self.editor.grid(row=2,column=0,sticky='nsew')
            y = ttk.Scrollbar(right,command=self.editor.yview); y.grid(row=2,column=1,sticky='ns'); self.editor.configure(yscrollcommand=y.set)
            x = ttk.Scrollbar(right,orient='horizontal',command=self.editor.xview); x.grid(row=3,column=0,sticky='ew'); self.editor.configure(xscrollcommand=x.set)
            ttk.Label(right,text='Shell output (scripts are not sandboxed)',foreground='#9b2323').grid(row=4,column=0,sticky='w',pady=(10,4))
            self.output = tk.Text(right,height=7,wrap='word',state='disabled',font=('DejaVu Sans Mono',9))
            self.output.grid(row=5,column=0,sticky='ew')
            pane.add(right, weight=3)
        self.populate()
        self.timer = self.frame.after(100,self.poll)

    def selected_paths(self):
        return tuple(self.directory / self.tree.item(i,'text') for i in self.tree.selection())

    def selection_changed(self, event=None):
        paths = self.selected_paths()
        self.status.set(f'{len(paths)} selected. Folder: {self.directory}')
        if self.selection_callback:
            self.selection_callback(paths)

    def populate(self):
        p, rows = list_directory(self.directory)
        self.tree.delete(*self.tree.get_children())
        for name,kind,size in rows:
            self.tree.insert('', 'end', text=name, values=(kind,size))
        self.path_var.set(str(p))

    def navigate(self, path):
        try:
            p, _ = list_directory(path)
            self.directory = p; self.populate()
            self.status.set(f'Folder: {p}')
        except Exception as e:
            self.mb.showerror('Cannot open folder', str(e), parent=self.frame)

    def choose_folder(self):
        name = self.fd.askdirectory(initialdir=self.directory, parent=self.frame)
        if name: self.navigate(name)

    def open_selected(self, event=None):
        paths = self.selected_paths()
        if len(paths)!=1: return
        p=paths[0]
        if p.is_dir(): self.navigate(p)
        elif not self.select_only: self.open_text()

    def dirty(self):
        return self.loaded_text is not None and self.editor.get('1.0','end-1c') != self.loaded_text

    def abandon(self):
        if not self.dirty(): return True
        answer=self.mb.askyesnocancel('Unsaved edits','Save edits before leaving this file?',parent=self.frame)
        if answer is None: return False
        return self.save() if answer else True

    def open_text(self):
        paths=self.selected_paths()
        if len(paths)!=1:
            self.mb.showinfo('Choose one file','Select one UTF-8 text or shell file.',parent=self.frame);return
        if not self.abandon():return
        try:
            text,raw=read_text(paths[0])
            self.open_path=paths[0];self.original=raw;self.loaded_text=text
            self.editor.delete('1.0','end');self.editor.insert('1.0',text);self.editor.edit_reset()
            self.editor_title.set(str(self.open_path))
        except Exception as e:self.mb.showerror('Cannot edit file',str(e),parent=self.frame)

    def save(self):
        if self.open_path is None:return self.save_as()
        if not self.mb.askyesno('Save changes',f'Overwrite this file?\n{self.open_path}',parent=self.frame):return False
        try:
            text=self.editor.get('1.0','end-1c');self.original=save_text(self.open_path,text,self.original);self.loaded_text=text
            self.status.set('Saved '+str(self.open_path));return True
        except Exception as e:self.mb.showerror('Save failed',str(e),parent=self.frame);return False

    def save_as(self):
        name=self.fd.asksaveasfilename(initialdir=self.directory,parent=self.frame,confirmoverwrite=False)
        if not name:return False
        p=Path(name)
        if not self.mb.askyesno('Review save path',f'Save text to:\n{p}\n'+('Existing file will be overwritten.' if p.exists() else 'New file will be created.'),parent=self.frame):return False
        try:
            raw=read_text(p)[1] if p.exists() else None
            text=self.editor.get('1.0','end-1c');self.original=save_text(p,text,raw,allow_new=True)
            self.open_path=p;self.loaded_text=text;self.editor_title.set(str(p));self.populate();return True
        except Exception as e:self.mb.showerror('Save failed',str(e),parent=self.frame);return False

    def run_shell(self):
        if self.process is not None:
            self.mb.showinfo('Script running','Stop the current script first.',parent=self.frame);return
        paths=self.selected_paths()
        if len(paths)!=1:return
        try:cmd,cwd=shell_command(paths[0])
        except Exception as e:self.mb.showerror('Cannot run',str(e),parent=self.frame);return
        if self.dirty() and self.open_path==paths[0]:
            self.mb.showinfo('Unsaved edits','Save or discard edits before running this script.',parent=self.frame);return
        if not self.mb.askyesno('Run trusted script?',f'{cmd[1]}\nWorking folder: {cwd}\n\nThis script can change or delete files, access the network and start other programs. It is NOT sandboxed. Only run code you trust. Run now?',parent=self.frame):return
        try:
            self.process=subprocess.Popen(cmd,cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0,start_new_session=True)
            self.append_output('Running '+cmd[1]+'\n')
            proc=self.process
            def worker():
                total=0
                while True:
                    chunk=proc.stdout.read(4096)
                    if not chunk:break
                    if total<1024*1024:self.events.put(('output',chunk[:1024*1024-total].decode('utf-8','replace')))
                    total+=len(chunk)
                self.events.put(('done',proc.wait()))
            threading.Thread(target=worker,daemon=True).start()
        except Exception as e:self.process=None;self.mb.showerror('Run failed',str(e),parent=self.frame)

    def stop_shell(self):
        if self.process and self.process.poll() is None:
            import signal
            try:os.killpg(self.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            self.status.set('Stop requested. Detached child processes may continue.')

    def append_output(self,text):
        self.output.configure(state='normal');self.output.insert('end',text);self.output.see('end');self.output.configure(state='disabled')

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='output':self.append_output(value)
                elif kind=='done':self.append_output(f'\nExit status: {value}\n');self.process=None
        except queue.Empty:pass
        if self.frame.winfo_exists():self.timer = self.frame.after(100,self.poll)

    def close(self):
        if not self.select_only and not self.abandon():return False
        if self.process and self.process.poll() is None:
            if not self.mb.askyesno('Script still running','Request stop and close? Detached children may keep running.',parent=self.frame):return False
            self.stop_shell()
        self.frame.after_cancel(self.timer)
        return True


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',nargs='?');parser.add_argument('--version',action='store_true');args=parser.parse_args()
    if args.version:print(VERSION);return 0
    try:
        tk,ttk,mb,fd=_tk();root=tk.Tk();root.title('FileFinder+');root.geometry('1120x720');root.minsize(900,600)
        ttk.Style().theme_use('clam');browser=BrowserFrame(root,args.folder);browser.frame.pack(fill='both',expand=True)
        root.protocol('WM_DELETE_WINDOW',lambda:root.destroy() if browser.close() else None);root.mainloop();return 0
    except Exception as e:
        print('FileFinder+ needs Python Tk and a desktop display (local desktop or VNC). '+str(e));return 2

if __name__=='__main__':raise SystemExit(main())
