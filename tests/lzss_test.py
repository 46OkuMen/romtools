import unittest

from romtools.lzss import pointer_offset, flag_length, interpret_flag


class TestLZSS(unittest.TestCase):
    def test_pointer_offset(self):
        self.assertEqual(pointer_offset(0x0000), 0x12)
        self.assertEqual(pointer_offset(0x0700), 0x19)
        self.assertEqual(pointer_offset(0x3800), 0x4a)
        self.assertEqual(pointer_offset(0x4401), 0x56)
        self.assertEqual(pointer_offset(0x4c14), 0x15e)
        self.assertEqual(pointer_offset(0x3920), 0x24b)

    def test_flag_length(self):
        self.assertEqual(flag_length('0x00'), 16)
        self.assertEqual(flag_length('0xFF'), 8)
        self.assertEqual(flag_length('0x7c'), 11)

    def test_interpret_flag(self):
        self.assertEqual(interpret_flag('0x00'), interpret_flag(0))
        self.assertEqual(interpret_flag('0x00'), [False] * 8)
        self.assertEqual(interpret_flag('0xff'), [True] * 8)
        self.assertEqual(interpret_flag('0x7c'),
                         [False, False, True, True, True, True, True, False])
        self.assertEqual(interpret_flag('0x76'),
                         [False, True, True, False, True, True, True, False])
