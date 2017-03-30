"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

(Currently using an unofficial English translation by kuoushi)
"""

from locale import getpreferredencoding
from os import path, pardir, remove, mkdir
from shutil import copyfile
from subprocess import check_output, CalledProcessError
from romtools.lzss import compress

NDC_PATH = path.abspath(__file__) 

SUPPORTED_FILE_FORMATS = ['fdi', 'hdi', 'hdm', 'flp', 'vmdk', 'dsk', 'vfd', 'vhd',
                          'hdd', 'img', 'd88', 'tfd', 'thd', 'nfd', 'nhd', 'h0', 'h1',
                          'h2', 'h3', 'h4', 'slh']

HARD_DISK_FORMATS = ['hdi', 'nhd', 'slh', 'vhd', 'hdd', 'thd']
# HDI: anex86
# THD: T98
# NHD: T98-Next
# VHD: VirtualPC (created by euee)
# SLH: SL9821

def file_to_string(file_path, start=0, length=0):
    # Defaults: read full file from start.
    # TODO: The default file path for this causes some real problems...
    with open(file_path, 'rb') as f:
        f.seek(start)
        if length:
            return f.read(length)
        else:
            return f.read()

class FileNotFoundError(Exception):
    def __init__(self, message, errors):
        super(FileNotFoundError, self).__init__(message)

class UnicodePathError(Exception):
    def __init__(self, message, errors):
        super(UnicodePathError, self).__init__(message)

class Disk:
    def __init__(self, filename, backup_folder=None):
        self.filename = filename
        self.extension = filename.split('.')[-1].lower()
        assert self.extension in SUPPORTED_FILE_FORMATS # TODO use an exception

        self.original_extension = self.extension
        self.dir = path.abspath(path.join(filename, pardir))

        if backup_folder is None:
            self._backup_filename = path.join(self.dir, 'backup', path.basename(self.filename))
        else:
            if not path.isdir(backup_folder):
                mkdir(backup_folder)
            self._backup_filename = path.join(backup_folder, path.basename(self.filename))

        #if not path.isdir(path.join(self.dir, 'backup')):
        #    mkdir(path.join(self.dir, 'backup'))

        print self._backup_filename

    def extract(self, filename, path_in_disk=None, dest_path=None, lzss=False):
        # TODO: Add lzss decompress support.

        cmd = 'ndc G "%s" 0 ' % (self.filename)
        if path_in_disk:
            cmd += path.join(path_in_disk, filename)
        else:
            cmd += filename

        if dest_path is None:
            dest_path = self.dir

        cmd += ' "' + dest_path + '"'
        print cmd
        try:
            result = check_output(cmd)
        except CalledProcessError:
            raise FileNotFoundError('File not found in disk', [])
        except UnicodeEncodeError:
            raise UnicodePathError("Non-Latin characters in path", [])

        #return Gamefile(filename, self)

    def delete(self, filename, path_in_disk=None):
        filename_without_path = filename.split('\\')[-1]
        del_cmd = 'ndc D "%s" 0' % (self.filename)
        if path_in_disk:
            del_cmd += ' "' + path.join(path_in_disk, filename_without_path) + '"'
        else:
            del_cmd += ' "' + filename_without_path  + '"'
        #print del_cmd
        result = check_output(del_cmd)

    def insert(self, filepath, path_in_disk=None):
        # First, delete the original file in the disk if applicable.

        filename = path.basename(filepath)
        self.delete(filename, path_in_disk)


        cmd = 'ndc P "%s" 0 %s' % (self.filename, filepath)
        if path_in_disk:
            cmd += ' ' + path_in_disk
        #print cmd
        result = check_output(cmd)

    def backup(self):
        copyfile(self.filename, self._backup_filename)

    def restore_from_backup(self):
        copyfile(self._backup_filename, self.filename)
        #remove(self._backup_filename)

    def __repr__(self):
        return self.filename

class Gamefile(object):
    def __init__(self, path, disk=None, dest_disk=None, pointer_constant=None):
        self.path = path
        self.filename = path.split('\\')[-1]
        self.disk = disk
        self.dest_disk = dest_disk

        self.original_filestring = file_to_string(path)
        self.filestring = "" + self.original_filestring
        with open(path, 'rb') as f:
            self.length = len(f.read())

        self.pointer_constant = pointer_constant

    def write(self, path_in_disk='.', compression=False):
        """Write the new data to an independent file for later inspection."""
        dest_path = path.join(self.dest_disk.dir, self.filename)

        with open(dest_path, 'wb') as fileopen:
            fileopen.write(self.filestring)

        if compression:
            print 'compressing now'
            compressed_path = compress(dest_path)
            print compressed_path
            dest_path = compressed_path

        print "inserting:", dest_path
        self.dest_disk.insert(dest_path, path_in_disk=path_in_disk)

    def edit(self, location, data):
        """Write data to a particular location."""
        self.filestring = self.filestring[:location] + data + self.filestring[location+len(data):]
        assert len(self.filestring) == len(self.original_filestring)
        return self.filestring

    def __repr__(self):
        return self.filename

class Block(object):
    """A text block.

    Attributes:
        gamefile: The EXEFile or DATFile object it belongs to.
        start = Beginning offset of the block.
        stop  = Ending offset of the block.
        original_blockstring: Hex string of entire block.
        blockstring: Hex string of entire block for editing.
        translations: List of Translation objects.
        """

    def __init__(self, gamefile, (start, stop)):
        self.gamefile = gamefile
        self.start = start
        self.stop = stop

        self.original_blockstring = file_to_string(self.gamefile.disk.filename)
        self.blockstring = "" + self.original_blockstring

    def __repr__(self):
        return "%s (%s, %s)" % (self.gamefile, hex(self.start), hex(self.stop))


if __name__ == '__main__':
    #EVODisk = Disk('46OM.hdi')
    #EVODisk.insert('windhex.cfg')

    EVOHDM = Disk('EVO.hdm')
    EVOHDM.insert('AV300.GDT')
    EVOHDM.extract('AV300.GDT')

# TODO: This backup folder is going into the weird pyinstaller land.