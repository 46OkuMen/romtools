"""
    Tests for pachy98.
    You must supply your own disks in the original_roms directory.
"""

import unittest
import os, sys, shutil
import ndcpy
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

EVO_HDI_PATH = os.path.join(ROM_DIR, EVO_HDI)
EVO_FD_PATHS = [os.path.join(ROM_DIR, fd) for fd in EVO_FDs]

EVO_CFG = 'Pachy98-EVO.json'

EVO_CFG_PATH = os.path.join(CFG_DIR, EVO_CFG)

class EvoHDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(EVO_CFG_PATH, EVO_CFG)
        shutil.copy(EVO_HDI_PATH, EVO_HDI)

    def tearDown(self):
        os.remove(EVO_CFG)
        os.remove(EVO_HDI)

    def test_patch(self):
        assert os.path.exists(EVO_HDI)
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\n')

        assert b"Error. Restoring from backup..." not in p.stdout
        assert b"target window checksum mismatch" not in p.stdout

class EvoFDTest(unittest.TestCase):
    def setUp(self):
        shutil.copy(EVO_CFG_PATH, EVO_CFG)

        for fd in EVO_FDs:
            shutil.copy(os.path.join(ROM_DIR, fd), fd)


    def tearDown(self):
        os.remove(EVO_CFG)
        for fd in EVO_FDs:
            os.remove(fd)

    def test_patch(self):
        p = run(['python', 'pachy98.py'], stdout=PIPE, input=b'y\n')

        assert b"Error. Restoring from backup..." not in p.stdout
        assert b"target window checksum mismatch" not in p.stdout
