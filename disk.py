"""
Utils for extracting and replacing files in disk images.
The standard tool to do this is EditDisk/DiskExplorer, but that has no CLI,
so we have to use a rather obscure Japanese utility called NDC.exe, found here:

http://euee.web.fc2.com/tool/nd.html

NDC version is Ver.0 alpha05d 2017/06/11.
"""
import logging
from os import path, pardir, mkdir
from shutil import copyfile
from subprocess import check_output, CalledProcessError
from ndc import NDC, NDCPermissionError

#from lzss import compress

SUPPORTED_FILE_FORMATS = ['fdi', 'hdi', 'hdm', 'dip', 'flp', 'vmdk', 'dsk',
                          'vfd', 'vhd', 'hdd', 'img', 'd88', 'tfd', 'thd',
                          'nfd', 'nhd', 'h0', 'h1', 'h2', 'h3', 'h4', 'slh',
                          'dcp', 'xdf', 'dup', 'fdd', 'slf']

HARD_DISK_FORMATS = ['hdi', 'nhd', 'slh', 'vhd', 'hdd', 'thd']
# HDI: anex86
# THD: T98
# NHD: T98-Next
# VHD: VirtualPC (created by euee)
# SLH: SL9821

# Don't know anything about the DIP format, but this seems to be the common
# header:
DIP_HEADER = b'\x01\x08\x00\x13\x41\x00\x01'


def is_valid_disk_image(filename):
    # logging.info("Checking is_valid_disk_image on %s" % filename)
    just_filename = path.split(filename)[1]
    if just_filename.lower().split('.')[-1] in SUPPORTED_FILE_FORMATS:
        return True
    elif len(just_filename.split('.')) == 1:
        return is_DIP(filename)


def is_DIP(target):
    """Detect a DIP file if extension not specified."""
    # logging.info("Calling is_DIP on %s" % target)
    try:
        with open(target, 'rb') as f:
            file_header = f.read(7)
            return file_header == DIP_HEADER
    except IOError:
        return False
    except FileNotFoundError:
        return False


class FileNotFoundError(Exception):
    def __init__(self, message, errors=[]):
        super(FileNotFoundError, self).__init__(message)


class ReadOnlyDiskError(Exception):
    def __init__(self, message, errors):
        super(ReadOnlyDiskError, self).__init__(message)


class FileFormatNotSupportedError(Exception):
    def __init__(self, message, errors=[]):
        super(FileFormatNotSupportedError, self).__init__(message)


class Disk:
    def __init__(self,
                 filename,
                 backup_folder=None,
                 dump_excel=None,
                 pointer_excel=None,
                 ndc_dir=''):
        self.filename = filename

        just_filename = path.split(filename)[1]
        self.extension = path.splitext(just_filename)[1].lstrip('.').lower()

        # If there's no extension, it won't get split at the period
        if len(self.extension) == 0:
            if is_DIP(self.filename):
                self.extension = 'dip'

        if self.extension not in SUPPORTED_FILE_FORMATS:
            raise FileFormatNotSupportedError('Disk format "%s" is not supported' % self.extension)

        self.dir = path.abspath(path.join(filename, pardir))

        if backup_folder is None:
            self._backup_filename = path.join(self.dir, 'backup',
                                              path.basename(self.filename))
        else:
            if not path.isdir(backup_folder):
                mkdir(backup_folder)
            self._backup_filename = path.join(backup_folder,
                                              path.basename(self.filename))

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
        self.ndc = NDC(self.ndc_path)
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

        return filenames, subdirs

    def find_file(self, target_file):
        results = self.ndc.find_all(self.filename, target_file)
        #print(results)
        # remove filename
        result_hit_dirs = [r[0][:-1 * (len(target_file))]
                           for r in results]
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

    def extract(self, filename, path_in_disk='', dest_path=None, lzss=False):
        # TODO: Add lzss decompress support.

        image_path = path.join(path_in_disk, filename)
        self.ndc.get(self.filename, image_path, dest_path or self.dir)

    def delete(self, filename, path_in_disk=''):
        self.ndc.delete(
            image=self.filename,
            path=path.join(path_in_disk, filename),
            partition=0
        )

    def insert(self,
               filepath,
               path_in_disk='',     # used to be None
               delete_original=True,
               delete_necessary=False):
        # First, delete the original file in the disk if applicable.

        filename = path.basename(filepath)
        if delete_original:
            try:
                self.ndc.delete(
                    image=self.filename,
                    path=path.join(path_in_disk, filename),
                    )
                #self.ndc.delete(self.filename, filename)
            except NDCPermissionError:
                if delete_necessary:
                    raise
                else:
                    print("Couldn't delete, but continuing anyway")

        self.ndc.put(self.filename, filepath, path_in_disk or '')

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
    def __init__(self, path, disk=None, dest_disk=None, pointer_constant=0, pointer_sheet_name=None):
        self.path = path
        self.filename = path.split('\\')[-1]
        self.disk = disk
        self.dest_disk = dest_disk

        if pointer_sheet_name is None:
            pointer_sheet_name = self.filename

        with open(path, 'rb') as f:
            self.original_filestring = f.read()
        self.filestring = self.original_filestring
        with open(path, 'rb') as f:
            self.length = len(f.read())

        assert len(self.original_filestring) == len(self.filestring) == self.length

        self.pointer_constant = pointer_constant

        if self.disk:
            if self.disk.pointer_excel:
                self.pointers = self.disk.pointer_excel.get_pointers(self, pointer_sheet_name)
            else:
                self.pointers = None
        else:
            self.pointers = None

    def write(self, path_in_disk=None, compression=False, skip_disk=False):
        """Write the new data to an independent file for later inspection."""

        # Don't double-path a file already in 'patched'
        if 'patched' not in self.filename:
            dest_path = path.join(self.dest_disk.dir, self.filename)

        with open(dest_path, 'wb') as fileopen:
            fileopen.write(self.filestring)

        if compression:
            print('compressing now')
            compressed_path = compress(dest_path)
            print(compressed_path)
            dest_path = compressed_path

        if not skip_disk:
            print("inserting:", dest_path)
            self.dest_disk.insert(dest_path, path_in_disk=path_in_disk)
        return dest_path

    def incorporate(self, block):
        i = self.filestring.index(block.original_blockstring)
        #print("Original blockstring found at", i)
        self.filestring = self.filestring.replace(block.original_blockstring,
                                                  block.blockstring)

    def edit(self, location, data):
        """Write data to a particular location."""
        self.filestring = (self.filestring[:location] + data +
                           self.filestring[location + len(data):])
        return self.filestring

    def edit_pointers_in_range(self, rng, diff):
        """Edit all the pointers between two file offsets."""
        start, stop = rng
        #print("Editing pointers in range %s %s with diff %s" % (hex(start), hex(stop), hex(diff)))
        if diff != 0:
            #print([p for p in range(start+1, stop+1)])
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

    def __init__(self, gamefile, interval):
        (start, stop) = interval
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


class Overflow(object):
    """An overflowing string.

    """

    # o[0] is location, o[1] is the string, o[2] is the parent block, o[3] is
    # the first string's original location

    def __init__(self, location, string, parent_block, first_string_location):
        self.location = location
        self.string = string
        self.block = parent_block
        self.first_string_location = first_string_location

    def move(spare):
        pass


if __name__ == '__main__':

    EVOHDM = Disk('EVO.hdm')
    EVOHDM.insert('AV300.GDT')
    EVOHDM.extract('AV300.GDT')

