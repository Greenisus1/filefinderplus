"""Headless FileFinder+ browser with a line editor and explicit trusted shell run."""
from pathlib import Path
import os
import subprocess
import signal
from filefinderplus import list_directory,read_text,save_text,shell_command
from terminal_ui import run

def insert_line(lines,index,value):
 """Preserve logical line separation when appending after a final unterminated line."""
 if not 0<=index<=len(lines):raise ValueError('Line number out of range.')
 if index>0 and lines[index-1] and not lines[index-1].endswith(('\n','\r')):lines[index-1]+='\n'
 lines.insert(index,value+'\n')

def edit(ui,path):
 text,original=read_text(path);lines=text.splitlines(keepends=True);dirty=False
 while True:
  action=ui.menu(str(path),['View buffer','Replace line','Insert line','Delete line','Save','Save as','Back'+(' (unsaved changes)' if dirty else '')])
  if action is None or action==6:
   if not dirty or ui.confirm('Discard unsaved edits?'):return
  elif action==0:ui.message(''.join(lines))
  elif action in (1,2,3):
   value=ui.prompt('Line number (1-based)'+(' to insert before; last+1 appends' if action==2 else ''))
   if value is None:continue
   try:n=int(value)-1
   except ValueError:ui.message('Enter a line number.');continue
   if n<0 or n>(len(lines) if action==2 else len(lines)-1):ui.message('Line number out of range.');continue
   if action==3:
    if ui.confirm('Delete line '+str(n+1)+'?'):lines.pop(n);dirty=True
   else:
    new=ui.prompt('New line text (newline added)')
    if new is not None:
     if action==1:lines[n]=new+'\n'
     else:insert_line(lines,n,new)
     dirty=True
  elif action in (4,5):
   target=path
   if action==5:
    value=ui.prompt('Save as full path')
    if not value:continue
    target=Path(value).expanduser().absolute()
   if not ui.confirm('Save '+str(target)+(' - overwrite existing file?' if target.exists() else ' - create new file?')):continue
   raw=original if target==path else read_text(target)[1] if target.exists() else None
   original=save_text(target,''.join(lines),raw,allow_new=action==5);path=target;dirty=False;ui.message('Saved '+str(target))

def run_script(ui,path):
 cmd,cwd=shell_command(path)
 ui.message('Script: '+cmd[1]+'\nWorking folder: '+cwd+'\nNOT sandboxed. Can change/delete files, use network, launch programs with your permissions. Output will run in your terminal. Only trust your own scripts. Ctrl-C requests stop. Terminal control codes are not filtered while the trusted script runs.')
 if not ui.confirm('Run this trusted script?'):return
 def execute():
  proc=subprocess.Popen(cmd,cwd=cwd,stdin=subprocess.DEVNULL,start_new_session=True)
  try:code=proc.wait()
  except KeyboardInterrupt:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:code=proc.wait(timeout=3)
   except subprocess.TimeoutExpired:
    if input('Script ignored stop. Kill process group? [y/N] ').lower()=='y':
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     code=proc.wait()
    else:code='still running; detached children may remain'
  print('\nExit:',code)
  try:input('Enter to return to FileFinder+: ')
  except (EOFError,KeyboardInterrupt):pass
 ui.external(execute)

def browse(ui,start=None):
 folder=Path(start or Path.home()).expanduser().resolve()
 while True:
  try:
   folder,rows=list_directory(folder)
   labels=['↑ Parent folder','⌂ Home','Open folder by path']+[name+'  ['+kind+']'+('  '+size+' bytes' if size else '') for name,kind,size in rows]
   index=ui.menu(str(folder),labels)
   if index is None:return
   if index==0:folder=folder.parent;continue
   if index==1:folder=Path.home();continue
   if index==2:
    value=ui.prompt('Folder path')
    if value:folder,_=list_directory(value)
    continue
   name,kind,size=rows[index-3];path=folder/name
   if kind=='Folder':folder=path;continue
   choice=ui.menu(str(path),['View UTF-8 text','Edit UTF-8 text','Run trusted .sh','Back'])
   if choice==0:ui.message(read_text(path)[0])
   elif choice==1:edit(ui,path)
   elif choice==2:run_script(ui,path)
  except (OSError,ValueError,UnicodeError) as e:ui.message(str(e))

def launch(start=None):return run('FileFinder+ 1.1.3',lambda ui:browse(ui,start))

def pick_paths(ui,start=None):
 """Reusable multiselect picker; no editing/execution. Returns immutable paths."""
 folder=Path(start or Path.home()).expanduser().resolve();selected=set()
 while True:
  try:
   folder,rows=list_directory(folder)
   labels=['Done: '+str(len(selected))+' selected','Cancel selection','Parent folder','Open folder by path']+[('[x] ' if folder/name in selected else '[ ] ')+name+' ['+kind+']' for name,kind,size in rows]
   index=ui.menu(str(folder),labels)
   if index is None or index==1:return ()
   if index==0:return tuple(sorted(selected))
   if index==2:folder=folder.parent;continue
   if index==3:
    value=ui.prompt('Folder path')
    if value:folder,_=list_directory(value)
    continue
   name,kind,size=rows[index-4];path=folder/name
   if kind=='Folder':
    action=ui.menu(str(path),['Open folder','Toggle whole folder selection','Back'])
    if action==0:folder=path;continue
    if action!=1:continue
   if path in selected:selected.remove(path)
   else:selected.add(path)
  except (OSError,ValueError) as e:ui.message(str(e))
