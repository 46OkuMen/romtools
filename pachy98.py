from sys import argv, exit
from os import listdir, remove
from shutil import copyfile
from os.path import isfile, splitext
from os.path import join as pathjoin
from romtools.disk import Disk, HARD_DISK_FORMATS, ReadOnlyDiskError
from romtools.patch import Patch, PatchChecksumError
import json
import codecs

if __name__== '__main__':
    print("Pachy98 v0.0.1 by 46 OkuMen")
    with open('Rusty-cfg.json', 'r', encoding='shift_jis') as f:
        cfg = json.load(f)
        info = cfg['info']
        print("Patching: %s (%s) %s by %s ( %s )" % (info['game'], info['language'], info['version'], info['author'], info['authorsite']))
        #print(json.dumps(cfg, indent=4))

        expected_image_length = len([i for i in cfg['images'] if i['type'] != 'disabled'])

        selected_images = []
        hd_found = False

        print(argv)

        if len(argv) > 1:
            # Filenames have been provided as arguments.
            if len(argv) == 2:
                if argv[1].split('.')[-1].lower() in HARD_DISK_FORMATS:
                    selected_images = [argv[1],]
            elif len(argv) > 2:
                selected_images = argv[1:]

        if len(selected_images) not in (0, 1, expected_image_length):
            print("Received the wrong number of files as arguments.")
            exit()

        # TODO: Need to handle combinations of these two cases:
            # 1) selected_images has some of the right images, but not all.
            # 2) selected_images are in the wrong order.

        # Search the current directory for the right files
        for image in cfg['images']:
            if image['type'] == 'mixed':
                for common in image['hdd']['common']:
                    if isfile(common):
                        print(common, "was found in the current directory")
                        selected_images = [common,]
                        hd_found = True
                        break
                if not hd_found:
                    for common in image['floppy']['common']:
                        if isfile(common):
                            selected_images.append(common)
                            print(common, "was found in the current directory")
            elif image['type'] == 'floppy' and not hd_found:
                for common in image['floppy']['common']:
                    if isfile(common):
                        selected_images.append(common)
                        print(common, "was found in the current directory")

        print(selected_images)
        assert len(selected_images) in (1, expected_image_length)

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
                copyfile(f['name'], f['name'] + '_edited')

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
                    patchfile = Patch(f['name'], patch_filepath, edited=f['name'] + '_edited')
                    try:
                        patchfile.apply()
                        patch_worked = True
                    except PatchChecksumError:
                        continue

                if not patch_worked:
                    DiskImage.restore_from_backup()
                    remove(f['name'])
                    remove(f['name'] + '_edited')
                    print("Patch checksum error. This disk is not compatible with this patch, or is already patched.")
                    exit()

                copyfile(f['name'] + '_edited', f['name'])
                if not options['delete_all_first']:
                    DiskImage.insert(f['name'], path_in_disk)
                    remove(f['name'])
                    remove(f['name'] + '_edited')

            if options['delete_all_first']:
                for f in files:
                    try:
                        DiskImage.delete(f['name'], path_in_disk)
                    except ReadOnlyDiskError:
                        print("Error deleting", f, ". Make sure the disk is not read-only, and try again.")
                        DiskImage.restore_from_backup()
                        exit()
                for f in files:
                    DiskImage.insert(f['name'], path_in_disk, delete_original=False)
                    remove(f['name'])
                    remove(f['name'] + '_edited')
        print("Patching complete! Read the README and enjoy the game.")


    #print(listdir('.'))

# Changes made to the json:
# Removed all 'disabled' disks
# Could probably get rid of "value" as well
