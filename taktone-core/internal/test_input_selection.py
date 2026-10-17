import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import convert


class FolderInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.stock=self.folder/'Digitakt_OS1.53.syx'
        self.stock.write_bytes(b'stock')
        profile=SimpleNamespace(file_sha256=hashlib.sha256(b'stock').hexdigest())
        self.profiles=patch.object(convert,'PROFILES',[profile])
        self.profiles.start()
        self.addCleanup(self.profiles.stop)

    def test_stock_only(self):
        (self.folder/'taktone-Digitakt_OS1.53.syx').write_bytes(b'generated')
        self.assertEqual(convert.choose_input(self.folder),self.stock)

    def test_added_mod_is_used_instead_of_stock(self):
        mod=self.folder/'my-mod.syx';mod.write_bytes(b'mod')
        self.assertEqual(convert.choose_input(self.folder),mod)

    def test_multiple_inputs_require_a_choice(self):
        for name in ('one.syx','two.syx'):(self.folder/name).write_bytes(name.encode())
        with patch.object(convert.sys.stdin,'isatty',return_value=False):
            with self.assertRaisesRegex(ValueError,'More than one input'):
                convert.choose_input(self.folder)
        with patch.object(convert.sys.stdin,'isatty',return_value=True),patch('builtins.input',return_value='2'):
            self.assertEqual(convert.choose_input(self.folder),self.folder/'two.syx')

    def test_empty_folder_explains_setup(self):
        self.stock.unlink()
        with self.assertRaisesRegex(ValueError,'firmware/'):
            convert.choose_input(self.folder)


if __name__=='__main__':unittest.main()
