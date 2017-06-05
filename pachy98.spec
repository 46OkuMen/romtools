# -*- mode: python -*-

block_cipher = None


a = Analysis(['pachy98.py'],
             pathex=['C:\\Users\\maxsi\\romtools'],
             binaries=[],
             datas=[('pachy.ico', '.'),],
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
