"""
Utils for creating xdelta patches.
"""

import os

class Patch:
	def __init__(self, original, edited):
		self.original = original
		self.edited = edited

	def create(self, path_filename):
		cmd = "xdelta3 -s %s %s %s" % (self.original, self.edited, path_filename)
		print cmd
		os.system(cmd)


if __name__ == '__main__':
	EVOPatch = Patch('EVO-Original.hdi', 'EVO-Patched.hdi')
	EVOPatch.create('patch.xdelta')