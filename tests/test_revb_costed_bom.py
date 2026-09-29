import subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RevBCostedBomTest(unittest.TestCase):
 def test_costed_bom_covers_native_source(self):
  p=subprocess.run([sys.executable,str(ROOT/"tools/check_revb_costed_bom.py")],cwd=ROOT,text=True,capture_output=True)
  self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr); self.assertIn("439 physical refs",p.stdout)
if __name__=="__main__": unittest.main()
