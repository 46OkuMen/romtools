"""
Utils for creating xdelta patches.
"""
from subprocess import check_output, CalledProcessError
from shutil import copyfile

class PatchChecksumError(Exception):
    def __init__(self, message, errors):
        super(PatchChecksumError, self).__init__(message)

class Patch:
    def __init__(self, original, edited, filename):
        self.original = original
        self.edited = edited
        self.filename = filename        

    def create(self):
        cmd = 'xdelta3 -f -s "%s" "%s" "%s' % (self.original, self.edited, self.filename)
        try:
            result = check_output(cmd)
        except CalledProcessError:
            raise Exception('Something went wrong', [])

    def apply(self):
        print self.original, self.edited
        copyfile(self.original, self.edited)
        cmd = 'xdelta3 -f -d -s "%s" "%s" "%s"' % (self.original, self.filename, self.edited)  # SOURCE OUT TARGET
        print cmd
        try:
            result = check_output(cmd)
        except CalledProcessError:
            raise PatchChecksumError('Target file had incorrect checksum', [])


if __name__ == '__main__':
    EVOPatch = Patch('EVO-Original.hdi', 'EVO-Patched.hdi', 'EVOPatch.xdelta')
    EVOPatch.create()
