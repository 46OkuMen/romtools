# -*- mode: python -*-

block_cipher = None


a = Analysis(['pachy98.py'],
             pathex=['C:\\Users\\maxsi\\romtools'],
             binaries=[],
             datas=[('pachy.ico', '.'), ('schema.json', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='pachy98',
          debug=False,
          strip=False,
          upx=False,
          console=True,
          windowed=False,
          icon='pachy.ico')

############################################
# Code-sign the generated executable
import subprocess
import shutil
from pachy98 import VERSION, MS_VERSION
subprocess.call(["./verpatch", "dist/pachy98.exe", "/va", MS_VERSION, "/pv", MS_VERSION])
subprocess.call(["./verpatch", "dist/pachy98.exe", "/s", "description", "Pachy98"])
subprocess.call(["./verpatch", "dist/pachy98.exe", "/s", "CompanyName", "46 OkuMen"])
subprocess.call(["./verpatch", "dist/pachy98.exe", "/s", "ProductName", "Pachy98"])
subprocess.call(["./verpatch", "dist/pachy98.exe", "/s", "LegalCopyright", "Copyright (c) 2018"])
subprocess.call(["./signtool", "sign", "/a", "/t", "http://timestamp.comodoca.com", "dist/pachy98.exe"])

shutil.copyfile('bin/xdelta3.exe', 'dist/bin/xdelta3.exe')
shutil.copyfile('bin/NDC.exe', 'dist/bin/NDC.exe')

shutil.copyfile('pachy-readme.txt', 'dist/pachy-readme.txt')

shutil.copyfile('LICENSE', 'dist/LICENSE')

subprocess.call(['7z', 'a', 'dist/Pachy98 %s.zip' % VERSION, './dist/pachy98.exe', './dist/bin/', './dist/LICENSE',
                 './dist/pachy-readme.txt'])