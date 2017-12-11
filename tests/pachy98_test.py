"""
    Tests for pachy98.
    You must supply your own disks in the original_roms directory.
    There are quite a few, mostly from Neo Kobe.
"""

import unittest
import os
import shutil
from subprocess import run, PIPE
#from romtools.disk import Disk, Gamefile, Block, Overflow
#from romtools.dump import DumpExcel, PointerExcel

ROM_DIR = 'original_roms'
CFG_DIR = 'pachy98_configs'

EVO_HDI = '46 Okunen Monogatari - The Shinkaron.hdi'
EVO_FDs = ['46 Okunen Monogatari - The Sinkaron (J) A user.FDI',
           '46 Okunen Monogatari - The Sinkaron (J) B 1.FDI',
           '46 Okunen Monogatari - The Sinkaron (J) B 2.FDI',
           '46 Okunen Monogatari - The Sinkaron (J) B 3.FDI',
           '46 Okunen Monogatari - The Sinkaron (J) B 4.FDI', ]

RUSTY_HDI = 'Rusty.hdi'
RUSTY_FDs = ['Rusty (Game disk A).hdm',
             'Rusty (Game disk B).hdm',
             'Rusty (Game disk C).hdm',
             'Rusty (Opening disk).hdm',
             'Rusty (System disk).hdm', ]

CRW_FDs = ['CRW_data1.FDI',
           'CRW_data2.FDI',
           'CRW_demo.FDI',
           'CRW_system.FDI',]

EVO_HDI_PATH = os.path.join(ROM_DIR, EVO_HDI)
RUSTY_HDI_PATH = os.path.join(ROM_DIR, RUSTY_HDI)

EVO_CFG = 'Pachy98-EVO.json'
RUSTY_CFG = 'Pachy98-Rusty.json'
CRW_CFG = 'Pachy98-CRW.json'
BRANDISH2_CFG = 'Pachy98-br2r.json'

EVO_CFG_PATH = os.path.join(CFG_DIR, EVO_CFG)
RUSTY_CFG_PATH = os.path.join(CFG_DIR, RUSTY_CFG)
CRW_CFG_PATH = os.path.join(CFG_DIR, CRW_CFG)

# TODO: I'd love to auto-generate these classes...


class EvoHDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(EVO_CFG_PATH, EVO_CFG)
        shutil.copy(EVO_HDI_PATH, EVO_HDI)

    def tearDown(self):
        os.remove(EVO_CFG)
        os.remove(EVO_HDI)

    @unittest.skip('No disk image')
    def test_patch(self):
        assert os.path.exists(EVO_HDI)
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\n')

        penultimate_line = p.stdout.splitlines()[-2]
        assert b'Patching complete!' in penultimate_line


class EvoFDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(EVO_CFG_PATH, EVO_CFG)

        for fd in EVO_FDs:
            shutil.copy(os.path.join(ROM_DIR, fd), fd)

    def tearDown(self):
        os.remove(EVO_CFG)
        for fd in EVO_FDs:
            os.remove(fd)

    @unittest.skip('No disk image')
    def test_patch(self):
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\n')

        penultimate_line = p.stdout.splitlines()[-2]
        assert b'Patching complete!' in penultimate_line


class RustyHDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(RUSTY_CFG_PATH, RUSTY_CFG)
        shutil.copy(RUSTY_HDI_PATH, RUSTY_HDI)

    def tearDown(self):
        os.remove(RUSTY_CFG)
        os.remove(RUSTY_HDI)

    @unittest.skip('No disk image')
    def test_patch(self):
        assert os.path.exists(RUSTY_HDI)
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\ny\n')

        penultimate_line = p.stdout.splitlines()[-2]
        assert b'Patching complete!' in penultimate_line


class RustyFDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(RUSTY_CFG_PATH, RUSTY_CFG)

        for fd in RUSTY_FDs:
            shutil.copy(os.path.join(ROM_DIR, fd), fd)

    def tearDown(self):
        os.remove(RUSTY_CFG)
        for fd in RUSTY_FDs:
            os.remove(fd)

    @unittest.skip('No disk image')
    def test_patch(self):
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\ny\n')

        penultimate_line = p.stdout.splitlines()[-2]
        assert b'Patching complete!' in penultimate_line


class CRWFDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(CRW_CFG_PATH, CRW_CFG)

        for fd in CRW_FDs:
            shutil.copy(os.path.join(ROM_DIR, fd), fd)

    def tearDown(self):
        os.remove(CRW_CFG)
        for fd in CRW_FDs:
            os.remove(fd)

    @unittest.skip('No disk image')
    def test_patch(self):
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\n')

        penultimate_line = p.stdout.splitlines()[-2]
        assert b'Patching complete!' in penultimate_line
