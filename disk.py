"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

"""


import os
# TODO: Use subprocess instead of os.system to check the output and see if it worked.
from shutil import copyfile

NDC_PATH = os.path.abspath(__file__) 

SUPPORTED_FILE_FORMATS = ['fdi', 'hdi', 'hdm', 'flp', 'vmdk', 'dsk', 'vfd', 'vhd',
                          'hdd', 'img', 'd88', 'tfd', 'thd', 'nfd', 'nhd', 'h0', 'h1',
                          'h2', 'h3', 'h4', 'hdm', 'slh']
# (hdm requires conversion to flp, but that conersion gets done below)

class Disk:
    def __init__(self, filename):
        self.filename = filename
        self.extension = filename.split('.')[-1].lower()
        assert self.extension in SUPPORTED_FILE_FORMATS # TODO use an exception

        self.original_extension = self.extension
        self.abspath = os.path.abspath(os.path.join(filename, os.pardir))

        if self.extension == 'hdm':
            new_disk_filename = self.filename.split('.')[0] + '.flp'
            copyfile(self.filename, new_disk_filename)
            self.filename = new_disk_filename


    def extract(self, filename, path_in_disk=None):
        # TODO: Add path_in_disk support.

        cmd = 'ndc G %s 0 %s .' % (self.filename, filename)
        os.system(cmd)

    def delete(self, filename, path_in_disk=None):
        del_cmd = 'ndc D %s 0' % (self.filename)
        if path_in_disk:
            del_cmd += ' ' + os.path.join(path_in_disk, filename)
        else:
            del_cmd += ' ' + filename
        os.system(del_cmd)

    def insert(self, filename, path_in_disk=None):
        # First, delete the original file in the disk if applicable.
        # (TODO: this may not be necessary?? check it agian)
        self.delete(filename, path_in_disk)

        cmd = 'ndc P %s 0 %s' % (self.filename, filename)
        if path_in_disk:
            cmd += ' ' + path_in_disk
        os.system(cmd)

        if self.original_extension == 'hdm':
            original_disk_filename = self.filename.split('.')[0] + '.hdm'
            copyfile(self.filename, original_disk_filename)

"""
kuoushi's note:
    Commands for using NDC to export/import/delete files:
    ndc G imgname.ext partition [pathtofileinimg]  exportfolder
    This command exports all or some files from the image. If you want to extract a certain file from an image 
    into the folder where ndc is located you would use this command, for example: 

    ndc G img.hdi 0 certainfolder\file.txt .

    The last . is important, it tells ndc to put the file in the same location

    ndc P imgname.ext partition filetoimport destination

    To put the same file  from above back into the place you found it, you'd do something like the following: 
    ndc P img.hdi 0 file.txt certainfolder

    Delete is similar: ndc D img.hdi 0 filetodelete

    Supported filetypes listed here:
    http://euee.web.fc2.com/tool/nd.html

"""

if __name__ == '__main__':
    #EVODisk = Disk('46OM.hdi')
    #EVODisk.insert('windhex.cfg')

    EVOHDM = Disk('EVO.hdm')
    EVOHDM.insert('AV300.GDT')
    EVOHDM.extract('AV300.GDT')