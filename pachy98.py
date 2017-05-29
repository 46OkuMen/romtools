from sys import argv, exit
from os import listdir, remove
from shutil import copyfile
from os.path import isfile, splitext
from os.path import split as pathsplit
from os.path import join as pathjoin
from disk import Disk, HARD_DISK_FORMATS, SUPPORTED_FILE_FORMATS, ReadOnlyDiskError, FileNotFoundError
from patch import Patch, PatchChecksumError
import json
import codecs

def is_valid_disk_image(filename):
    return filename.split('.')[-1] in SUPPORTED_FILE_FORMATS or len(filename.split('.')) == 1

if __name__== '__main__':
    print("Pachy98 v0.0.1 by 46 OkuMen")
    with open('EVO-cfg.json', 'r', encoding='utf-8') as f:
        # Load everything into a Unicode string first to handle SJIS text.
        # (Wish there was a slightly easier way)
        unicode_safe = f.read()
        cfg = json.loads(unicode_safe)
        #cfg = json.load(f)
        info = cfg['info']
        print("Patching: %s (%s) %s by %s ( %s )" % (info['game'], info['language'], info['version'], info['author'], info['authorsite']))
        #print(json.dumps(cfg, indent=4))

        expected_image_length = len([i for i in cfg['images'] if i['type'] != 'disabled'])

        selected_images = []
        arg_images = []
        hd_found = False

        print(argv)

        # ['pachy98.exe', 'arg1', 'arg2',] etc
        if len(argv) > 1:
            # Filenames have been provided as arguments.
            if len(argv) == 2:
                if argv[1].split('.')[-1].lower() in HARD_DISK_FORMATS:
                    arg_images = [argv[1],]
            elif len(argv) > 2:
                arg_images = argv[1:]

        #if len(arg_images) not in (0, 1, expected_image_length):
        #    print("Received the wrong number of files as arguments.")
        #    exit()

        # TODO: Need to handle combinations of these two cases:
            # 1) selected_images has some of the right images, but not all.
            # 2) selected_images are in the wrong order.

        # Ensure they're in the right order by checking their contents.
        for image in cfg['images']:
            image_found = False
            for arg_image in arg_images:
                ArgDisk = Disk(arg_image)
                try:
                    ArgDisk.find_file_dir(image['floppy']['files'])
                    selected_images.append(arg_image)
                    image_found = True
                except FileNotFoundError:
                    continue

            if not image_found:
                selected_images.append(None)

        print(selected_images)

        # TODO: Better to check all the file contents in this directory than use filenames.
        if len([s for s in  selected_images if s is not None]) == 0:
        # Otherwise, search the directory for common image names
            for image in cfg['images']:
                if image['type'] == 'mixed':
                    for common in image['hdd']['common']:
                        if isfile(common):
                            print(common, "was found in the current directory")
                            selected_images = [common,]
                            hd_found = True
                            break
                    if not hd_found:
                        floppy_found = False
                        for common in image['floppy']['common']:
                            if isfile(common):
                                selected_images.append(common)
                                print(common, "was found in the current directory")
                                floppy_found = True
                        if not floppy_found:
                            selected_images.append(None)
                elif image['type'] == 'floppy' and not hd_found:
                    floppy_found = False
                    for common in image['floppy']['common']:
                        if isfile(common):
                            selected_images.append(common)
                            floppy_found = True
                            print(common, "was found in the current directory")
                            break

                    if not floppy_found:
                        selected_images.append(None)

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

        # Parse options
        options = {}
        options['delete_all_first'] = False
        for o in cfg['options']:
            if o['type'] == 'checkbox':
                print(o['description'], "(y/n)")
                choice = input(">")
                while choice not in ('y', 'n'):
                    print("(y/n)")
                    choice = input(">")
                    choice = choice.strip(" ").lower()[0]
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
            DiskImage.backup()

            if DiskImage.extension in HARD_DISK_FORMATS:
                files = image['hdd']['files']
            else:
                files = image['floppy']['files']

            # Find the right directory to look for the files in.
            path_in_disk = DiskImage.find_file_dir(files)

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
                    elif f['patch']['type'] == 'checkbox':
                        if options[f['patch']['id']]:
                            patch_list = [f['patch']['checked'],]
                        else:
                            patch_list = [f['patch']['unchecked'],]
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
                    exit()

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
                        exit()
                for f in files:
                    extracted_file_path = pathjoin(disk_directory, f['name'])
                    DiskImage.insert(extracted_file_path, path_in_disk, delete_original=False)
                    remove(extracted_file_path)
                    remove(extracted_file_path + '_edited')
        print("Patching complete! Read the README and enjoy the game.")


    #print(listdir('.'))

# Changes made to the json:
# Removed all 'disabled' disks
# Could probably get rid of "value" as well
