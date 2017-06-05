"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

NDC version is Ver.0 alpha05c 2017/05/04.
"""
from os import path, pardir, remove, mkdir
from shutil import copyfile
from subprocess import check_output, CalledProcessError

from lzss import compress

NDC_PATH = path.abspath(__file__)

SUPPORTED_FILE_FORMATS = ['fdi', 'hdi', 'hdm', 'dip', 'flp', 'vmdk', 'dsk',
                          'vfd', 'vhd', 'hdd', 'img', 'd88', 'tfd', 'thd',
                          'nfd', 'nhd', 'h0', 'h1', 'h2', 'h3', 'h4', 'slh']

HARD_DISK_FORMATS = ['hdi', 'nhd', 'slh', 'vhd', 'hdd', 'thd']
# HDI: anex86
# THD: T98
# NHD: T98-Next
# VHD: VirtualPC (created by euee)
# SLH: SL9821

DIP_HEADER = b'\x01\x08\x00\x13\x41\x00\x01'

def is_DIP(target):
    """Detect a DIP file if extension not specified."""
    try:
        with open(target, 'rb') as f:
            file_header = f.read(7)
            #print(repr(file_header))
            #print(repr(DIP_HEADER))
            return file_header == DIP_HEADER
    except FileNotFoundError:
        return False


class FileNotFoundError(Exception):
    def __init__(self, message, errors):
        super(FileNotFoundError, self).__init__(message)


class ReadOnlyDiskError(Exception):
    def __init__(self, message, errors):
        super(ReadOnlyDiskError, self).__init__(message)


class FileFormatNotSupportedError(Exception):
    def __init__(self, message, errors):
        super(FileFormatNotSupportedError, self).__init__(message)


class Disk:
    def __init__(self, filename, backup_folder=None, dump_excel=None, pointer_excel=None):
        self.filename = filename
        self.extension = filename.split('.')[-1].lower()

        # If there's no extension, it won't get split at the period
        #print(self.extension)
        #print(filename)
        if self.extension == filename.lower():
            if is_DIP(self.filename):
                self.extension = 'dip'

        if self.extension not in SUPPORTED_FILE_FORMATS:
            raise FileFormatNotSupportedError('Disk format "%s" is not supported' % self.extension, [])

        # self.original_extension = self.extension
        self.dir = path.abspath(path.join(filename, pardir))

        if backup_folder is None:
            self._backup_filename = path.join(self.dir, 'backup', path.basename(self.filename))
        else:
            if not path.isdir(backup_folder):
                mkdir(backup_folder)
            self._backup_filename = path.join(backup_folder, path.basename(self.filename))

        # if not path.isdir(path.join(self.dir, 'backup')):
        #    mkdir(path.join(self.dir, 'backup'))

        self.dump_excel = dump_excel
        self.pointer_excel = pointer_excel

    def check_fallback(self, filename, path_in_disk, fallback_path, dest_path=None):
        """Figure out if the fallback is necessary from an "extract" command."""

        cmd = 'ndc G "%s" 0 ' % (self.filename)
        if path_in_disk:
            cmd += '"%s"' % path.join(path_in_disk, filename)
        else:
            cmd += '"%s"' % filename

        if dest_path is None:
            dest_path = self.dir

        cmd += ' "' + dest_path + '"'

        if fallback_path and not path_in_disk:
            fallback_cmd = 'ndc G "%s" 0 ' % (self.filename)
            fallback_cmd += '"%s"' % path.join(fallback_path, filename)
            fallback_cmd += ' "' + dest_path + '"'
        else:
            fallback_cmd = None

        #try:
        #    print(cmd)
        #except:
        #    print(repr(cmd))

        try:
            result = check_output(cmd)
            fallback_necessary = False
        except CalledProcessError:
            try:
                print("Trying the fallback command:", fallback_cmd)
                result = check_output(fallback_cmd)
                fallback_necessary = True
            except CalledProcessError:
                fallback_necessary = False # Don't use the fallback, it just fails

        # TODO: Cleanup the extracted file        
        return fallback_necessary

    def listdir(self, subdir=''):
        """ Display all the filenames and subdirs in a given disk and subdir.
        """
        cmd = 'ndc "%s" 0 ' % (self.filename)
        if subdir:
            cmd += '"%s"' % subdir

        #print(cmd)
        try:
            result = check_output(cmd)
        except CalledProcessError:
            raise FileNotFoundError('Subdirectory not found in disk', [])

        result = [r.split(b'\t') for r in result.split(b'\r\n')]
        result = list(filter(lambda x: len(x) == 4, result))

        filenames = [r[0].decode('shift_jis') for r in result if r[2] != b'<DIR>']
        subdirs = [r[0].decode('shift_jis') for r in result if r[2] == b'<DIR>' and len(r[0].strip(b'.')) > 0]

        return filenames, subdirs

    def find_file_dir(self, filenames):
        """ Traverse the disk dirs to find the one that contains all relevant files.
        """
        dir_queue = ['']

        while dir_queue:
            this_dir = dir_queue.pop(0)
            this_dir_files, subdirs = self.listdir(this_dir)

            if all([f in this_dir_files for f in filenames]):
                return this_dir

            for d in subdirs:
                dir_queue.append(path.join(this_dir, d))

        raise FileNotFoundError("Could not find all the files in the same dir.", [])

    def extract(self, filename, path_in_disk=None, fallback_path=None, dest_path=None, lzss=False):
        # TODO: Add lzss decompress support.

        cmd = 'ndc G "%s" 0 ' % (self.filename)
        if path_in_disk:
            cmd +=  '"%s"' % path.join(path_in_disk, filename)
        else:
            cmd += '"%s"' % filename

        if dest_path is None:
            dest_path = self.dir

        cmd += ' "' + dest_path + '"'

        if fallback_path and not path_in_disk:
            fallback_cmd = 'ndc G "%s" 0 ' % (self.filename)
            fallback_cmd += '"%s"' % path.join(fallback_path, filename)
            fallback_cmd += ' "' + dest_path + '"'
        else:
            fallback_cmd = None

        #try:
        #    print(cmd)
        #except:
        #    print(repr(cmd))

        try:
            result = check_output(cmd)
        except CalledProcessError:
            try:
                print("Trying the fallback command:", fallback_cmd)
                result = check_output(fallback_cmd)
            except CalledProcessError:
                raise FileNotFoundError('File not found in disk', [])

        # return Gamefile(filename, self)

    def delete(self, filename, path_in_disk=None, fallback_path=None):
        filename_without_path = filename.split('\\')[-1]
        del_cmd = 'ndc D "%s" 0' % (self.filename)
        if path_in_disk:
            del_cmd += ' "' + path.join(path_in_disk, filename_without_path) + '"'
        else:
            del_cmd += ' "' + filename_without_path  + '"'

        if fallback_path and not path_in_disk:
            fallback_cmd = 'ndc D "%s" 0 ' % (self.filename)
            fallback_cmd += '"%s"' % path.join(fallback_path, filename)
        else:
            fallback_cmd = None

        #try:
        #    print(del_cmd)
        #except:
        #    print(repr(del_cmd))

        try:
            result = check_output(del_cmd)
        except CalledProcessError:
            if fallback_cmd:
                try:
                    #print("Trying the fallback command:", fallback_cmd)
                    result = check_output(fallback_cmd)
                except CalledProcessError:
                    raise ReadOnlyDiskError("Disk is in read-only mode", [])
            else:
                raise ReadOnlyDiskError("Disk is in read-only mode", [])

    def insert(self, filepath, path_in_disk=None, fallback_path=None, delete_original=True):
        # First, delete the original file in the disk if applicable.

        filename = path.basename(filepath)
        if delete_original:
            self.delete(filename, path_in_disk, fallback_path=fallback_path)

        cmd = 'ndc P "%s" 0 "%s"' % (self.filename, filepath)
        if path_in_disk:
            cmd += ' ' + path_in_disk

        if fallback_path and not path_in_disk:
            fallback_cmd = 'ndc P "%s" 0 "%s"' % (self.filename, filepath)
            fallback_cmd += fallback_path
        else:
            fallback_cmd = None

        #try:
        #    print(cmd)
        #except:
        #    print(repr(cmd))

        try:
            result = check_output(cmd)
        except CalledProcessError:
            try:
                #print("Trying the fallback command:", fallback_cmd)
                result = check_output(fallback_cmd)
            except CalledProcessError:
                raise FileNotFoundError("File not found in disk", [])

    def backup(self):
        copyfile(self.filename, self._backup_filename)

    def restore_from_backup(self):
        copyfile(self._backup_filename, self.filename)
        #remove(self._backup_filename)

    def __repr__(self):
        return self.filename


class Gamefile(object):
    def __init__(self, path, disk=None, dest_disk=None, pointer_constant=0):
        self.path = path
        self.filename = path.split('\\')[-1]
        self.disk = disk
        self.dest_disk = dest_disk

        with open(path, 'rb') as f:
            self.original_filestring = f.read()
        self.filestring = self.original_filestring
        with open(path, 'rb') as f:
            self.length = len(f.read())

        assert len(self.original_filestring) == len(self.filestring) == self.length

        self.pointer_constant = pointer_constant

        if self.disk:
            if self.disk.pointer_excel:
                self.pointers = self.disk.pointer_excel.get_pointers(self)
        else:
            self.pointers = None

    def write(self, path_in_disk=None, compression=False):
        """Write the new data to an independent file for later inspection."""
        dest_path = path.join(self.dest_disk.dir, self.filename)

        with open(dest_path, 'wb') as fileopen:
            fileopen.write(self.filestring)

        if compression:
            print('compressing now')
            compressed_path = compress(dest_path)
            print(compressed_path)
            dest_path = compressed_path

        print("inserting:", dest_path)
        self.dest_disk.insert(dest_path, path_in_disk=path_in_disk)

    def incorporate(self, block):
        self.filestring = self.filestring.replace(block.original_blockstring, block.blockstring)

    def edit(self, location, data):
        """Write data to a particular location."""
        self.filestring = self.filestring[:location] + data + self.filestring[location+len(data):]
        assert len(self.filestring) == len(self.original_filestring)
        return self.filestring

    def edit_pointers_in_range(self, rng, diff):
        """Edit all the pointers between two file offsets."""
        start, stop = rng
        print("Editing pointers in range %s %s" % (hex(start), hex(stop)))
        if diff != 0:
            for offset in [p for p in range(start+1, stop+1) if p in self.pointers]:
                for ptr in self.pointers[offset]:
                    ptr.edit(diff)

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

    def __init__(self, gamefile, xxx_todo_changeme):
        (start, stop) = xxx_todo_changeme
        self.gamefile = gamefile
        self.start = start
        self.stop = stop

        with open(self.gamefile.path, 'rb') as f:
            self.original_blockstring = f.read()[start:stop]
        self.blockstring = self.original_blockstring

    def incorporate(self):
        self.gamefile.incorporate(self)

    def __repr__(self):
        return "%s (%s, %s)" % (self.gamefile, hex(self.start), hex(self.stop))


if __name__ == '__main__':

    EVOHDM = Disk('EVO.hdm')
    EVOHDM.insert('AV300.GDT')
    EVOHDM.extract('AV300.GDT')

# TODO: This backup folder is going into the weird pyinstaller land.
