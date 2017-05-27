from sys import argv, exit
from os import listdir, remove
from shutil import copyfile
from os.path import isfile, splitext
from os.path import join as pathjoin
from romtools.disk import Disk, HARD_DISK_FORMATS
from romtools.patch import Patch, PatchChecksumError
import json

if __name__== '__main__':
    print("Pachy98 v0.0.1 by 46 OkuMen")
    print("Patching: E.V.O.: The Theory of Evolution")
    with open('EVO-cfg.json', 'r') as f:
        cfg = json.load(f)
        print(json.dumps(cfg, indent=4))

        expected_image_length = len([i for i in cfg['images'] if i['type'] != 'disabled'])

        selected_images = []
        hd_found = False

        if len(argv) > 1:
            # Filenames have been provided as arguments.
            if len(argv) == 2:
                if splitext(argv[1])[1] in HARD_DISK_FORMATS:
                    selected_images = [argv[1],]
            elif len(argv) > 2:
                selected_images = argv[1:]

        assert len(selected_images) in (0, 1, expected_image_length)

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
                if 'list' in f['patch']:
                    patch_list = f['patch']['list']
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
                    print("Patch checksum error")
                    exit()

                copyfile(f['name'] + '_edited', f['name'])
                DiskImage.insert(f['name'], path_in_disk)

                remove(f['name'])
                remove(f['name'] + '_edited')
        print("Patching complete! Read the README and enjoy the game.")


    #print(listdir('.'))

# Changes made to the json:
# Removed all 'disabled' disks
# Could probably get rid of "value" as well
# Could get rid of "type" for the patches, since I will just treat them all as failsafelists.
