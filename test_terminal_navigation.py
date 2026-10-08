import unittest,curses
from terminal_ui import UI
class Screen:
 def __init__(self,keys):self.keys=iter(keys)
 def getmaxyx(self):return (12,80)
 def get_wch(self):return next(self.keys)
class Tests(unittest.TestCase):
 def menu(self,keys,rows=None):
  ui=UI.__new__(UI);ui.s=Screen(keys);ui.draw=lambda *a,**k:None;return ui.menu('test',rows if rows is not None else list(map(str,range(50))))
 def test_pagedown(self):self.assertEqual(self.menu([curses.KEY_NPAGE,'\n']),6)
 def test_pageup(self):self.assertEqual(self.menu([curses.KEY_END,curses.KEY_PPAGE,'\n']),43)
 def test_end_home(self):self.assertEqual(self.menu([curses.KEY_END,curses.KEY_HOME,'\n']),0)
 def test_clamp(self):self.assertEqual(self.menu([curses.KEY_NPAGE,'\n'],['a','b']),1)
 def test_cancel(self):self.assertIsNone(self.menu(['q']))
if __name__=='__main__':unittest.main()
