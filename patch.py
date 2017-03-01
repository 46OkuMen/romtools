"""
Utils for creating xdelta patches.
"""

import os

class Patch:
	def __init__(self, original, edited, filename):
		self.original = original
		self.edited = edited
		self.filename = filename

	def create(self):
		cmd = 'xdelta3 -f -s "%s" "%s" "%s' % (self.original, self.edited, self.filename)
		os.system(cmd)

	def apply(self):
		cmd = 'xdelta3 -f -d "%s" "%s"' % (self.filename, self.edited)
		print cmd
		os.system(cmd)


if __name__ == '__main__':
	EVOPatch = Patch('EVO-Original.hdi', 'EVO-Patched.hdi')
	EVOPatch.create('patch.xdelta')

# TODO: Use subprocess.Popen to capture output and such.