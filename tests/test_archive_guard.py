"""Freeze the already merged PR18 snapshot, never a newly generated baseline."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import check_revb_repository as guard

class ArchiveGuardTests(unittest.TestCase):
    def test_freeze_matches_reviewed_pr18_merge(self):
        self.assertEqual(guard.BASE_TREE,'052a06c6e6e5b0ce23e94f75774a9f1cc7f3f167')

    def test_original_archive_cannot_silently_replace_reviewed_snapshot(self):
        fn=getattr(guard,'check_archive_tree',None)
        self.assertIsNotNone(fn,'archive tree validation must have its own test seam')
        with self.assertRaises(ValueError):fn('6ddd828a8b7ca289a4f2acfee7eb2e1f07569e2e')

    def test_unknown_tree_remains_rejected(self):
        fn=getattr(guard,'check_archive_tree',None)
        self.assertIsNotNone(fn,'missing strict archive tree validation')
        for value in ('0'*40,'',guard.BASE_TREE+'\n'):
            with self.subTest(value=value), self.assertRaises(ValueError):fn(value)
        fn(guard.BASE_TREE)

if __name__=='__main__':unittest.main()
