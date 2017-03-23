""" Basic configuration things you'd want to store about a rom.
"""

"""
	Directory layout and paths.
"""
SRC_ROM_FILENAME = ''
SRC_ROM_DIR = ''
SRC_ROM_PATH = os.path.join(SRC_ROM_DIR, SRC_ROM_FILENAME)

DEST_ROM_FILENAME = ''
SRC_ROM_DIR = ''
DEST_ROM_PATH = os.path.join(DEST_ROM_DIR, DEST_ROM_FILENAME)

"""
	Stuff about the disks themselves and what files are in them.
"""

# DISKS = ['A', 'B1', 'B2', 'B3', 'B4']
DISKS = []

# FILES_TO_PATCH = {'A': ['file1.exe', 'file2.exe'],
#                    'B': ['img2.gdt',],}
FILES_TO_PATCH = {}


"""
	Maps of individual files.
"""

FILE_BLOCKS = {}

"""
	Pointer info.
"""
POINTER_CONSTANT = {}
POINTER_REGEX = r''

"""
	Formatting stuff.
"""
LINE_LENGTH = 0
WINDOW_LINES = 3
NEWLINE_CHAR = '\n'

CONTROL_CODES = {}