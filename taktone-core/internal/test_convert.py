import unittest
from convert import merge, BASE


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.stock = bytes(256)
        self.core = bytearray(self.stock + b'payload')
        self.core[100:104] = b'hook'

    def test_preserves_disjoint_changes_and_core(self):
        mod = bytearray(self.stock)
        mod[10:14] = b'modd'
        result, report = merge(self.stock, mod, self.core)
        self.assertEqual(result[10:14], b'modd')
        self.assertEqual(result[100:104], b'hook')
        self.assertEqual(result[256:], b'payload')
        self.assertEqual(report['modified_bytes'], 4)

    def test_direct_and_context_conflicts(self):
        for at in (100, 99, 68, 135):
            with self.subTest(at=at):
                mod = bytearray(self.stock)
                mod[at] = 1
                image, report = merge(self.stock, mod, self.core)
                self.assertIsNone(image)
                self.assertTrue(report['conflicts'])

    def test_same_as_core_still_rejected(self):
        mod = bytearray(self.stock)
        mod[100:104] = b'hook'
        self.assertIsNone(merge(self.stock, mod, self.core)[0])

    def test_length_changes_rejected(self):
        for mod in (self.stock[:-1], self.stock+b'x'):
            with self.assertRaises(ValueError):
                merge(self.stock, mod, self.core)

    def test_ram_conflicts_and_exclusive_boundaries(self):
        for start, end in ((0x47BE0000, 0x47BE0010), (BASE+256, BASE+257)):
            self.assertIsNone(merge(self.stock, self.stock, self.core,
                                   [dict(start=start, end=end)])[0])
        self.assertIsNotNone(merge(self.stock, self.stock, self.core,
                                  [dict(start='0x47bdfff0', end='0x47be0000')])[0])
        with self.assertRaises(ValueError):
            merge(self.stock, self.stock, self.core, [dict(start=0x47BE0000, end=0x47BE0000)])


if __name__ == '__main__':
    unittest.main()
