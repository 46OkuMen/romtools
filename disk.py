"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

"""

import os

class Disk:
	def __init__(self, filename):
		self.filename = filename
		self.extension = filename.split('.')[-1]
		self.path = os.path.abspath(os.path.join(filename, os.pardir))


	def extract(self, filename):
		cmd = 'ndc G %s 0 %s .' % (diskname, filename)
		os.system(cmd)

	def insert(self, filename):
		cmd = 'ndc P %s 0 %s .' % (diskname, filename)
		os.system(cmd)

"""
kuoushi's note:
	Commands for using NDC to export/import/delete files:
	ndc G imgname.ext partition [pathtofileinimg]  exportfolder
	This command exports all or some files from the image. If you want to extract a certain file from an image into the folder where ndc is located you would use this command, for example: ndc G img.hdi 0 certainfolder\file.txt .
	The last . is important, it tells ndc to put the file in the same location

	ndc P imgname.ext partition filetoimport destination
	To put the same file  from above back into the place you found it, you'd do something like the following: ndc P img.hdi 0 file.txt certainfolder

	Delete is similar: ndc D img.hdi 0 filetodelete

	Supported filetypes listed here:
	http://euee.web.fc2.com/tool/nd.html

"""

if __name__ == '__main__':
	EVODisk = Disk('46OM.hdi')
	EVODisk.insert('windhex.cfg')