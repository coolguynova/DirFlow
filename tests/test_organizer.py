import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
import organizer

class TestFileOrganizer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher_tracked = patch('organizer.TRACKED_DIR', self.test_dir)
        self.mock_tracked = self.patcher_tracked.start()
        
    def tearDown(self):
        self.patcher_tracked.stop()
        shutil.rmtree(self.test_dir)
        
    def test_safe_destination(self):
        folder = os.path.join(self.test_dir, "Documents")
        os.makedirs(folder, exist_ok=True)
        
        file1 = os.path.join(folder, "test.pdf")
        with open(file1, "w") as f:
            f.write("hello")
            
        safe_path = organizer.FileSorterEngine.get_safe_destination(folder, "test.pdf")
        self.assertEqual(os.path.basename(safe_path), "test_(1).pdf")

    def test_file_routing(self):
        doc_file = os.path.join(self.test_dir, "report.pdf")
        with open(doc_file, "w") as f:
            f.write("some content")
            
        organizer.FileSorterEngine.process_file(doc_file)
        
        expected_dest = os.path.join(self.test_dir, "Documents", "report.pdf")
        self.assertTrue(os.path.exists(expected_dest))
        self.assertFalse(os.path.exists(doc_file))

    def test_deduplication(self):
        dest_folder = os.path.join(self.test_dir, "Documents")
        os.makedirs(dest_folder, exist_ok=True)
        
        # Write same file in dest
        with open(os.path.join(dest_folder, "dup.pdf"), "w") as f:
            f.write("identical content")
            
        # Write same file in root
        source_file = os.path.join(self.test_dir, "dup.pdf")
        with open(source_file, "w") as f:
            f.write("identical content")
            
        organizer.FileSorterEngine.process_file(source_file)
        
        # Source should be deleted, and duplicate counter should not create dup_(1).pdf
        self.assertFalse(os.path.exists(source_file))
        self.assertFalse(os.path.exists(os.path.join(dest_folder, "dup_(1).pdf")))
