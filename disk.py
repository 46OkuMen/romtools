"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

NDC version is Ver.0 alpha05d 2017/06/11.
"""
import logging
from os import path, pardir, remove, mkdir
from shutil import copyfile
from subprocess import check_output, CalledProcessError
from time import sleep

from lzss import compress

SUPPORTED_FILE_FORMATS = ['fdi', 'hdi', 'hdm', 'dip', 'flp', 'vmdk', 'dsk',
                          'vfd', 'vhd', 'hdd', 'img', 'd88', 'tfd', 'thd',
                          'nfd', 'nhd', 'h0', 'h1', 'h2', 'h3', 'h4', 'slh',
                          'dcp', 'xdf']

HARD_DISK_FORMATS = ['hdi', 'nhd', 'slh', 'vhd', 'hdd', 'thd']
# HDI: anex86
# THD: T98
# NHD: T98-Next
# VHD: VirtualPC (created by euee)
# SLH: SL9821

# Don't know anything about the DIP format, but this seems to be the common header:
DIP_HEADER = b'\x01\x08\x00\x13\x41\x00\x01'

def is_valid_disk_image(filename):
    #logging.info("Checking is_valid_disk_image on %s" % filename)
    just_filename = path.split(filename)[1]
    if just_filename.lower().split('.')[-1] in SUPPORTED_FILE_FORMATS:
        return True
    elif len(just_filename.split('.')) == 1:
        #logging.info("just_filename.lower().split('.') length is 1. trying is_DIP now")
        return is_DIP(filename)

def is_DIP(target):
    """Detect a DIP file if extension not specified."""
    #logging.info("Calling is_DIP on %s" % target)
    try:
        with open(target, 'rb') as f:
            file_header = f.read(7)
            return file_header == DIP_HEADER
    except IOError:
        return False
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
    def __init__(self, filename, backup_folder=None, dump_excel=None, pointer_excel=None, ndc_dir=''):
        self.filename = filename

        just_filename = path.split(filename)[1]
        self.extension = path.splitext(just_filename)[1].lstrip('.').lower()

        # If there's no extension, it won't get split at the period
        if len(self.extension) == 0:
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

        counter = 0
        while path.isfile(self._backup_filename):
            original = just_filename.split('.')[0]
            counter += 1
            if counter > 1:
                self._backup_filename = self._backup_filename.replace('-' + str(counter-1).zfill(2), '-' + str(counter).zfill(2))
            else:
                self._backup_filename = self._backup_filename.replace(original, original + "-" + str(counter).zfill(2))

        # if not path.isdir(path.join(self.dir, 'backup')):
        #    mkdir(path.join(self.dir, 'backup'))

        self.dump_excel = dump_excel
        self.pointer_excel = pointer_excel
        self.ndc_path = path.join(ndc_dir, 'ndc')
        self._file_dir_cache = {}

    def listdir(self, subdir=''):
        """ Display all the filenames and subdirs in a given disk and subdir.
        """
        try:
            subdir = subdir.decode()
        except AttributeError:
            pass
        subdir = subdir.rstrip('\\')
        cmd = '"%s" "%s" 0 ' % (self.ndc_path, self.filename)
        if subdir:
            cmd += '"%s"' % subdir

        logging.info(cmd)
        try:
            result = check_output(cmd)
        except CalledProcessError:
            raise FileNotFoundError('Subdirectory not found in disk', [])

        result = [r.split(b'\t') for r in result.split(b'\r\n')]
        result = list(filter(lambda x: len(x) == 4, result))

        filenames = []
        subdirs = []
        for r in result:
            try:
                decoded = r[0].decode('shift_jis')
                if r[2] != b'<DIR>':
                    filenames.append(decoded)
                elif r[2] == b'<DIR>' and len(r[0].strip(b'.')) > 0:
                    subdirs.append(decoded)
            except UnicodeDecodeError:
                logging.info("Couldn't decode one of the strings in the folder: %s" % subdir)
                continue

        #logging.info("Filenames: %s" % filenames)
        #logging.info("Subdirs: %s" % subdirs)
        print(filenames)
        return filenames, subdirs

    def find_file(self, target_file):
        cmd = '"%s" fa "%s" 0 "" "%s"' % (self.ndc_path, self.filename, target_file)
        logging.info(cmd)

        try:
            result = check_output(cmd)
        except CalledProcessError:
            return None
        result_hits = result.split(b'\r\n')
        result_hit_paths = [r.split(b'\t')[0] for r in result_hits]
        result_hit_paths = result_hit_paths[:-2]    # remove weird last two outputs
        result_hit_dirs = [r[:-1*(len(target_file))] for r in result_hit_paths] # remove filename
        if result_hit_paths and not result_hit_dirs:
            result_hit_dirs = [b'']
        # Returns an empty ilst if they're not found...
        return result_hit_dirs

        # How to handle files that are in the root?

    def find_file_dir(self, target_filenames, path_keywords=[]):
        # path_keywords not implemented
        if tuple(target_filenames) in self._file_dir_cache:
            return self._file_dir_cache[tuple(target_filenames)]

        first_find_output = self.find_file(target_filenames[0])
        if first_find_output is not None:
            for d in first_find_output:
                d_listdir = self.listdir(d)[0]
                if all([t in d_listdir for t in target_filenames]):
                    self._file_dir_cache[tuple(target_filenames)] = d.decode('utf-8')
                    return d.decode('utf-8')
        self._file_dir_cache[tuple(target_filenames)] = None
        return None
        #if len(find_first_output) == 0:
        #    return None
        #else:
        #    return list(common_dirs)[0].decode('utf-8')      # TODO: Not sure what to do if multiple results...?

    def extract(self, filename, path_in_disk=None, dest_path=None, lzss=False):
        # TODO: Add lzss decompress support.

        cmd = '"%s" G "%s" 0 ' % (self.ndc_path, self.filename)
        if path_in_disk:
            cmd +=  '"%s"' % path.join(path_in_disk, filename)
        else:
            cmd += '"%s"' % filename

        if dest_path is None:
            dest_path = self.dir

        cmd += ' "' + dest_path + '"'

        logging.info(cmd)

        try:
            result = check_output(cmd)
        except CalledProcessError:
            raise FileNotFoundError('File not found in disk', [])

        # return Gamefile(filename, self)

    def delete(self, filename, path_in_disk=None):
        filename_without_path = filename.split('\\')[-1]
        del_cmd = '"%s" D "%s" 0' % (self.ndc_path, self.filename)
        if path_in_disk:
            del_cmd += ' "' + path.join(path_in_disk, filename_without_path) + '"'
        else:
            del_cmd += ' "' + filename_without_path  + '"'

        try:
            result = check_output(del_cmd)
        except CalledProcessError:
            sleep(.5)
            try:
                result = check_output(del_cmd)
            except CalledProcessError:
                raise ReadOnlyDiskError("Disk is in read-only mode", [])

            raise ReadOnlyDiskError("Disk is in read-only mode", [])

    def insert(self, filepath, path_in_disk=None, delete_original=True):
        # First, delete the original file in the disk if applicable.

        filename = path.basename(filepath)
        if delete_original:
            self.delete(filename, path_in_disk)

        cmd = '"%s" P "%s" 0 "%s"' % (self.ndc_path, self.filename, filepath)
        if path_in_disk:
            cmd += ' ' + path_in_disk

        #print(cmd)
        logging.info(cmd)

        try:
            result = check_output(cmd)
        except PermissionError:
            sleep(.5)
            try:
                result = check_output(cmd)
            except CalledProcessError:
                raise FileNotFoundError("File not found in disk", [])
        except CalledProcessError:
            sleep(.5)
            try:
                result = check_output(cmd)
            except CalledProcessError:
                raise FileNotFoundError("File not found in disk", [])

    def backup(self):
        # Handle permissionerrors in client applications...
        copyfile(self.filename, self._backup_filename)

    def restore_from_backup(self):
        try:
            copyfile(self._backup_filename, self.filename)
        except PermissionError:
            print("Couldn't restore from the backup, but it is located at '%s'." % self._backup_filename)

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
