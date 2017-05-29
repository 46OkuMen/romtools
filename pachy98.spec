# -*- mode: python -*-

block_cipher = None


a = Analysis(['pachy98.py'],
             pathex=['C:\\Users\\maxsi\\code\\roms\\romtools'],
             binaries=[('NDC.exe', 'bin'),
                       ('xdelta3.exe', 'bin')],
             datas=[('46.ico', '.'),
                    ('patch/*.xdelta', 'patch'),],
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
          name='RustyPatcher',
          debug=True,
          strip=False,
          upx=True,
          console=True,
          windowed=False,
          icon='46.ico')
