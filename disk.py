"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

"""


import os
# TODO: Use subprocess instead of os.system to check the output and see if it worked.

# NDC.EXE is in the same directory as disk.py.
NDC_PATH = os.path.abspath(__file__) 

class Disk:
    def __init__(self, filename):
        self.filename = filename
        self.extension = filename.split('.')[-1]
        self.abspath = os.path.abspath(os.path.join(filename, os.pardir))


    def extract(self, filename):
        cmd = 'ndc G %s 0 %s .' % (self.filename, filename)
        print cmd
        os.system(cmd)

    def insert(self, filename, path_in_disk=None):
        #filename_path = os.path.join(self.abspath, filename)
        #filename_rel_path = os.path.relpath(filename_path, NDC_PATH)
        #print filename_rel_path

        del_cmd = 'ndc D %s 0' % (self.filename)

        if path_in_disk:
            del_cmd += ' ' + os.path.join(path_in_disk, filename)
        else:
            del_cmd += ' ' + filename
        os.system(del_cmd)

        cmd = 'ndc P %s 0 %s' % (self.filename, filename)
        if path_in_disk:
            cmd += ' ' + path_in_disk
        print cmd
        os.system(cmd)

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
    EVODisk = Disk('46OM.hdi')
    EVODisk.insert('windhex.cfg')