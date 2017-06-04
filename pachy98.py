import sys, os
from os import curdir, listdir, remove, getcwd, chdir
from shutil import copyfile
from os import access, W_OK
from os.path import isfile
from os.path import split as pathsplit
from os.path import join as pathjoin
from disk import Disk, HARD_DISK_FORMATS, SUPPORTED_FILE_FORMATS, ReadOnlyDiskError, FileNotFoundError, is_DIP
from patch import Patch, PatchChecksumError
import json

def is_valid_disk_image(filename):
    # TODO: How to handle directories?
    if filename.lower().split('.')[-1] in SUPPORTED_FILE_FORMATS:
        return True
    elif len(filename.split('.')) == 1:
        try:
            return is_DIP(filename)
        except PermissionError:
            return False

def y_n_input():
    print('(y/n)')
    user_input = input(">")
    user_input = user_input.strip(" ").lower()[0]
    while user_input not in ('y', 'n'):
        print('(y/n')
        user_input = input(">")
        user_input = user_input.strip(" ").lower()[0]

    return user_input


if __name__== '__main__':
    exe_dir = getcwd()
    if hasattr(sys, '_MEIPASS'):
        chdir(sys._MEIPASS)


    frozen = 'not'
    if getattr(sys, 'frozen', False):
        frozen = 'ever so'
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    print('we are', frozen, 'frozen')
    print('bundle dir is', bundle_dir)
    print('sys.argv[0] is', sys.argv[0])
    print('sys.executable is', sys.executable)
    print('os.getcwd is', os.getcwd())
    print('sys.path is', sys.path)

    # It can find the executables just fine right now.
    # TODO: How can I get it to find both the executables and the data in exe's dir?
    # Executables, when bundled, are in os.getcwd.
    # The data is in the same dir as sys.executable.
    # Do I need to just add the full sys.executable absolute path to all filenames invoked
    # as arguments???
    

    """
    if hasattr(sys, '_MEIPASS'):
        sys.path += sys._MEIPASS
    """

    print("Pachy98 v0.0.1 by 46 OkuMen")
    with open('Rusty-cfg.json', 'r', encoding='utf-8') as f:
        # Load everything into a Unicode string first to handle SJIS text.
        # (Wish there was a slightly easier way)
        unicode_safe = f.read()
        cfg = json.loads(unicode_safe)
        #cfg = json.load(f)
        info = cfg['info']
        print("Patching: %s (%s) %s by %s ( %s )" % (info['game'], info['language'], info['version'], info['author'], info['authorsite']))

        expected_image_length = len([i for i in cfg['images'] if i['type'] != 'disabled'])

        selected_images = [None,]*expected_image_length
        arg_images = []
        hd_found = False

        # ['pachy98.exe', 'arg1', 'arg2',] etc
        if len(sys.argv) > 1:
            # Filenames have been provided as arguments.
            arg_images = sys.argv[1:]

        # Ensure they're in the right order by checking their contents.
        for image in cfg['images']:
            image_found = False
            for arg_image in arg_images:
                ArgDisk = Disk(arg_image)
                try:
                    disk_filenames = [f['name'] for f in image['floppy']['files']]
                    ArgDisk.find_file_dir(disk_filenames)
                    selected_images[image['id']] = arg_image
                    image_found = True
                except FileNotFoundError:
                    continue

            if not image_found:
                selected_images[image['id']] = None

        images_in_dir = [f for f in listdir('.') if is_valid_disk_image(f)]

        #if len([s for s in  selected_images if s is not None]) == 0:
        # Otherwise, search the directory for common image names
        for image in cfg['images']:
            if image['type'] == 'mixed':
                hdd_filenames = [f['name'] for f in image['hdd']['files']]
                for dir_img in images_in_dir:
                    d = Disk(dir_img)
                    try:
                        _ = d.find_file_dir(hdd_filenames)
                        selected_images = [dir_img,]
                        hd_found = True
                        break
                    except FileNotFoundError:
                        pass

                if not hd_found:
                    floppy_filenames = [f['name'] for f in image['floppy']['files']]
                    floppy_found = False
                    #for common in image['floppy']['common']:
                    #    if isfile(common):
                    for dir_img in images_in_dir:
                        d = Disk(dir_img)
                        try:
                            _ = d.find_file_dir(floppy_filenames)
                            selected_images[image['id']] = dir_img
                            #print(dir_img, "was found in the current directory")
                            floppy_found = True
                            break
                        except FileNotFoundError:
                            pass

                    if not floppy_found:
                        print("No disk found for '%s'" % image['name'])
                        selected_images[image['id']] = None

            elif image['type'] == 'floppy' and not hd_found:
                floppy_found = False
                floppy_filenames = [f['name'] for f in image['floppy']['files']]
                for dir_img in images_in_dir:
                    d = Disk(dir_img)
                    try:
                        _ = d.find_file_dir(floppy_filenames)
                        selected_images[image['id']] = dir_img
                        floppy_found = True
                        print(dir_img, "was found in the current directory")
                        break
                    except FileNotFoundError:
                        pass

                if not floppy_found:
                    print("No disk found for '%s'" % image['name'])
                    selected_images[image['id']] = None

        print(selected_images)
        if len([i for i in selected_images if i is not None]) not in (1, expected_image_length):
            print("Could not auto-detect all your disks. Close this and drag them all onto Pachy98.EXE, or enter the filenames manually here:")
            for image in cfg['images']:
                if selected_images[image['id']] is None:
                    filename = ''
                    while not isfile(filename) or not is_valid_disk_image(filename):
                        filename = input("%s filename:\n>" % image['name'])
                        if not isfile(filename):
                            print("File doesn't exist.")
                        elif not is_valid_disk_image(filename):
                            print("File is not a supported disk image type.")
                    selected_images[image['id']] = filename

        print("Patch these disk images?\n")
        if len(selected_images) == 1:
            print("%s: %s" % ("Game HDD", selected_images[0]))
        else:
            for image in cfg['images']:
                print("%s: %s" % (image['name'], selected_images[image['id']]))

        confirmation = y_n_input()
        if confirmation.strip(" ".lower()[0]) == 'n':
            sys.exit()

        # Parse options
        options = {}
        options['delete_all_first'] = False
        for o in cfg['options']:
            if o['type'] == 'boolean':
                print(o['description'])
                choice = y_n_input()
                if choice == 'y':
                    options[o['id']] = True
                else:
                    options[o['id']] = False
            elif o['type'] == 'silent':
                if o['id'] == 'delete_all_first':
                    options['delete_all_first'] = True

        for i, disk_path in enumerate(selected_images):
            image = cfg['images'][i]
            disk_directory = pathsplit(disk_path)[0]
            DiskImage = Disk(disk_path, backup_folder='backup')

            if not access(disk_path, W_OK):
                print('Can\'t access the file "%s". Make sure the file is not read-only.' % cfg['images'][i]['name'])
                input()
                sys.exit()

            DiskImage.backup()

            if DiskImage.extension in HARD_DISK_FORMATS:
                files = image['hdd']['files']
            else:
                files = image['floppy']['files']

            # Find the right directory to look for the files in.
            disk_filenames = [f['name'] for f in files]
            path_in_disk = DiskImage.find_file_dir(disk_filenames)

            for f in files:
                print(f)
                DiskImage.extract(f['name'], path_in_disk)
                extracted_file_path = pathjoin(disk_directory, f['name'])
                copyfile(extracted_file_path, extracted_file_path + '_edited')

                # Failsafe list. Patches to try in order.
                patch_list = []
                if 'type' in f['patch']:
                    if f['patch']['type'] == 'failsafelist':
                        patch_list = f['patch']['list']
                    elif f['patch']['type'] == 'boolean':
                        if options[f['patch']['id']]:
                            patch_list = [f['patch']['true'],]
                        else:
                            patch_list = [f['patch']['false'],]
                else:
                    patch_list = [f['patch'],]

                patch_worked = False
                for patch in patch_list:
                    patch_filepath = pathjoin('patch', patch)
                    patchfile = Patch(extracted_file_path, patch_filepath, edited=extracted_file_path + '_edited')
                    try:
                        patchfile.apply()
                        patch_worked = True
                    except PatchChecksumError:
                        continue

                if not patch_worked:
                    DiskImage.restore_from_backup()
                    remove(extracted_file_path)
                    remove(extracted_file_path + '_edited')
                    print("Patch checksum error. This disk is not compatible with this patch, or is already patched.")
                    input()
                    sys.exit()

                copyfile(extracted_file_path + '_edited', extracted_file_path)
                if not options['delete_all_first']:
                    DiskImage.insert(extracted_file_path, path_in_disk)
                    remove(extracted_file_path)
                    remove(extracted_file_path + '_edited')

            if options['delete_all_first']:
                for f in files:
                    try:
                        DiskImage.delete(f['name'], path_in_disk)
                    except ReadOnlyDiskError:
                        print("Error deleting", f, ". Make sure the disk is not read-only, and try again.")
                        DiskImage.restore_from_backup()
                        input()
                        sys.exit()
                for f in files:
                    extracted_file_path = pathjoin(disk_directory, f['name'])
                    DiskImage.insert(extracted_file_path, path_in_disk, delete_original=False)
                    remove(extracted_file_path)
                    remove(extracted_file_path + '_edited')
        print("Patching complete! Read the README and enjoy the game.")


# Changes made to the json:
# Removed all 'disabled' disks
# Could probably get rid of "value" as well
# Can get rid of 'common' in each image.
