import importlib.util,pathlib,unittest
H=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("v",H/"verification_sync.py");v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class T(unittest.TestCase):
 def test_parse(self):
  m=v.normalize(v.parse("### REQ-ID\nREQ-ENC-001\n### TC-ID\nTC-ENC-SW-001\n### Verification Level\nrtl\n### Result\nPASS\n"))
  self.assertTrue(v.tracked(m));self.assertEqual(m["level"],"仿真/RTL");self.assertEqual(m["status"],"Verified")
 def test_untracked(self):self.assertFalse(v.tracked(v.parse("hello")))
 def test_half(self):
  with self.assertRaises(ValueError):v.tracked({"req_id":"REQ-X-001"})
 def test_blank(self):self.assertEqual(v.clean("_No response_"),"")
 def test_pid(self):self.assertEqual(v.pid("https://app.notion.com/p/3e45ebb61696819399dee00001e2cbf4?pvs=204"),"3e45ebb6-1696-8193-99de-e00001e2cbf4")
 def test_merge_not_pass(self):
  ev={"repository":{"full_name":"magic-alt/hil_lab"},"number":7,"pull_request":{"number":7,"html_url":"https://github.com/x/y/pull/7","body":"### REQ-ID\nREQ-X-001\n### TC-ID\nTC-X-001","title":"x","state":"closed","merged":True,"head":{"sha":"abc"},"updated_at":"2026-09-23T01:00:00Z"}}
  e=v.entity(ev);p=v.props(e,v.normalize(v.parse(e["body"])));self.assertEqual(e["state"],"merged");self.assertNotIn("Result",p)
if __name__=="__main__":unittest.main()
