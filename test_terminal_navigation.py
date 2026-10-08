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
class LineTests(unittest.TestCase):
 def test_unterminated_append(self):
  from terminal_browser import insert_line
  lines=['old'];insert_line(lines,1,'new');self.assertEqual(''.join(lines),'old\nnew\n')
 def test_existing_line_break(self):
  from terminal_browser import insert_line
  lines=['old\n'];insert_line(lines,1,'new');self.assertEqual(lines,['old\n','new\n'])
 def test_empty(self):
  from terminal_browser import insert_line
  lines=[];insert_line(lines,0,'new');self.assertEqual(lines,['new\n'])
if __name__=='__main__':unittest.main()
