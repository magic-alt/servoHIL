import importlib.util
import pathlib
import tempfile
import unittest
import os

H = pathlib.Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location("v", H / "verification_sync.py")
v = importlib.util.module_from_spec(s)
s.loader.exec_module(v)

class T(unittest.TestCase):
    def test_parse(self):
        m = v.normalize(v.parse(
            "### REQ-ID\nREQ-ENC-001\n"
            "### TC-ID\nTC-ENC-SW-001\n"
            "### Verification Level\nrtl\n"
            "### Result\nPASS\n"
        ))
        self.assertTrue(v.tracked(m))
        self.assertEqual(m["level"], "仿真/RTL")
        self.assertEqual(m["status"], "Verified")

    def test_untracked(self):
        self.assertFalse(v.tracked(v.parse("hello")))

    def test_half(self):
        with self.assertRaises(ValueError):
            v.tracked({"req_id": "REQ-X-001"})

    def test_blank(self):
        self.assertEqual(v.clean("_No response_"), "")

    def test_pid(self):
        self.assertEqual(
            v.pid("https://app.notion.com/p/3e45ebb61696819399dee00001e2cbf4?pvs=204"),
            "3e45ebb6-1696-8193-99de-e00001e2cbf4",
        )

    def test_trailing_body_heading(self):
        m = v.normalize(v.parse(
            "### REQ-ID\nREQ-X-001\n"
            "### TC-ID\nTC-X-001\n"
            "### Verification Status\nBlocked\n\n"
            "## Remaining work\n- keep this out of metadata\n"
        ))
        self.assertEqual(m["status"], "Blocked")

    def test_merge_not_pass(self):
        ev = {
            "repository": {"full_name": "magic-alt/hil_lab"},
            "number": 7,
            "action": "closed",
            "pull_request": {
                "number": 7,
                "html_url": "https://github.com/x/y/pull/7",
                "body": "### REQ-ID\nREQ-X-001\n### TC-ID\nTC-X-001",
                "title": "x",
                "state": "closed",
                "merged": True,
                "head": {"sha": "abc"},
                "updated_at": "2026-09-23T01:00:00Z",
            },
        }
        e = v.entity(ev)
        p = v.props(e, v.normalize(v.parse(e["body"])))
        self.assertEqual(e["state"], "merged")
        self.assertNotIn("Result", p)

    def test_dedicated_fields_do_not_clobber_curated_summary(self):
        e = {
            "type": "PR", "number": 9, "url": "https://github.com/x/y/pull/9",
            "repo": "magic-alt/hil_lab", "state": "open", "sha": "abc123",
            "updated": "2026-09-23T02:00:00Z", "action": "edited",
        }
        m = v.normalize({
            "req_id": "REQ-X-001", "tc_id": "TC-X-001",
            "evidence_path": "evidence/run-a", "hw": "revA", "fw": "deadbeef",
            "bitstream": "build-7", "result": "PASS", "status": "Verified",
        })
        p = v.props(e, m)
        self.assertEqual(p["GitHub PR"]["url"], e["url"])
        self.assertEqual(p["Git SHA"]["rich_text"][0]["text"]["content"], "abc123")
        self.assertEqual(p["Evidence Path"]["rich_text"][0]["text"]["content"], "evidence/run-a")
        self.assertEqual(p["HW Revision"]["rich_text"][0]["text"]["content"], "revA")
        self.assertNotIn("Evidence", p)
        self.assertNotIn("Commit/FW/Bitstream", p)
        self.assertNotIn("Issue/PR", p)

    def test_issue_and_pr_lifecycle_fields_are_separate(self):
        issue = {"type": "Issue", "number": 3, "url": "https://github.com/x/y/issues/3",
                 "repo": "magic-alt/hil_lab", "state": "open", "sha": "", "updated": "", "action": "edited"}
        pr = {"type": "PR", "number": 4, "url": "https://github.com/x/y/pull/4",
              "repo": "magic-alt/hil_lab", "state": "merged", "sha": "abcd", "updated": "", "action": "closed"}
        ip = v.props(issue, {})
        pp = v.props(pr, {})
        self.assertIn("GitHub Issue", ip)
        self.assertNotIn("GitHub PR", ip)
        self.assertIn("GitHub PR", pp)
        self.assertNotIn("GitHub Issue", pp)

    def test_explicit_evidence_date(self):
        m = v.normalize({"evidence_date": "2026-09-21", "result": "PASS"})
        p = v.props(
            {"type": "Issue", "number": 1, "url": "u", "repo": "", "state": "closed",
             "sha": "", "updated": "2026-09-23T00:00:00Z", "action": "edited"},
            m,
        )
        self.assertEqual(p["Evidence Date"]["date"]["start"], "2026-09-21")

    def test_bad_evidence_date(self):
        with self.assertRaises(ValueError):
            v.normalize({"evidence_date": "09/23/2026"})

    def test_pr_synchronize_invalidates_prior_verdict(self):
        e = {
            "type": "PR", "number": 9, "url": "https://github.com/x/y/pull/9",
            "repo": "magic-alt/hil_lab", "state": "open", "sha": "newhead",
            "updated": "2026-09-23T02:00:00Z", "action": "synchronize",
        }
        m = v.normalize({
            "req_id": "REQ-X-001", "tc_id": "TC-X-001",
            "result": "PASS", "status": "Verified",
            "evidence_path": "evidence/old-run",
        })
        p = v.props(e, m)
        self.assertEqual(p["Result"]["select"]["name"], "NOT RUN")
        self.assertEqual(p["Verification Status"]["select"]["name"], "Ready")
        self.assertEqual(p["Evidence Freshness"]["select"]["name"], "stale")
        self.assertNotIn("Evidence Date", p)
        self.assertNotIn("Evidence Git SHA", p)

    def test_pr_close_does_not_reapply_body_verdict(self):
        e = {
            "type": "PR", "number": 9, "url": "https://github.com/x/y/pull/9",
            "repo": "magic-alt/hil_lab", "state": "merged", "sha": "head",
            "updated": "2026-09-23T02:00:00Z", "action": "closed",
        }
        m = v.normalize({"result": "PASS", "status": "Verified"})
        p = v.props(e, m)
        self.assertNotIn("Result", p)
        self.assertNotIn("Verification Status", p)
        self.assertNotIn("Evidence Freshness", p)

    def test_explicit_pr_verdict_binds_evidence_to_head(self):
        e = {
            "type": "PR", "number": 9, "url": "https://github.com/x/y/pull/9",
            "repo": "magic-alt/hil_lab", "state": "open", "sha": "head123",
            "updated": "2026-09-23T02:00:00Z", "action": "edited",
        }
        m = v.normalize({"result": "PASS", "status": "Verified"})
        p = v.props(e, m)
        self.assertEqual(p["Evidence Freshness"]["select"]["name"], "current")
        self.assertEqual(p["Evidence Git SHA"]["rich_text"][0]["text"]["content"], "head123")

    def test_actions_outputs(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        old = os.environ.get("GITHUB_OUTPUT")
        os.environ["GITHUB_OUTPUT"] = path
        try:
            v.write_output("matrix_page_url", "https://notion.so/a")
            self.assertIn("matrix_page_url=https://notion.so/a", pathlib.Path(path).read_text())
        finally:
            if old is None:
                os.environ.pop("GITHUB_OUTPUT", None)
            else:
                os.environ["GITHUB_OUTPUT"] = old
            pathlib.Path(path).unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
