"""
        A command-line patching program for Japanese PC game disk images.
        Reads a json config file, looks for relevant disk images in 
"""

import sys, logging, json
from os import curdir, listdir, remove, getcwd, chdir, access, W_OK, stat, _exit
from shutil import copyfile
from os.path import isfile, isdir
from os.path import split as pathsplit
from os.path import join as pathjoin
from disk import Disk, HARD_DISK_FORMATS, SUPPORTED_FILE_FORMATS, is_valid_disk_image
from disk import ReadOnlyDiskError, FileNotFoundError, FileFormatNotSupportedError, is_DIP
from patch import Patch, PatchChecksumError
from urllib.request import urlopen
from urllib.error import HTTPError

VERSION = 'v0.16.0'

VALID_OPTION_TYPES = ['boolean', 'silent']
VALID_SILENT_OPTION_IDS = ['delete_all_first']
VALID_IMAGE_TYPES = ['floppy', 'hdd', 'mixed']
VALID_PATCH_TYPES = ['boolean', 'failsafelist']

class Config:
    def __init__(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            unicode_safe = f.read()
        self.json = json.loads(unicode_safe)
        self.info = self.json['info']
        self.images = self.json['images']
        self.options = self.json['options']

        for i in self.images:
            if i['type'] == 'mixed':
                self.all_filenames = [f['name'] for f in i['hdd']['files']]
                self.hdd_files = i['hdd']['files']
        self.patch_dir = pathjoin(pathsplit(json_path)[0], 'patch')

        # TODO: What other stuff do I need easier access to?
        if not self._validate_config():
            # TODO: Need a more specific message of what is wrong with it.
            message_wait_close("A config option in %s is not supported by this verison of Pachy98. Download a newer version." % selected_config)
        try:
            self._validate_patch_existence()
        except FileNotFoundError as e:
            message_wait_close("This config references a patch %s that doesn't exist." % e)


    def _validate_config(self):
        # TODO: More extensive validation.
            # Make sure all patches exist in the patch directory
            # Make sure booleaan id's match those defined by the user
            # Only one mixed or HDD, and it's in the 0th slot, right?
        for o in self.options:
            if o['type'] not in VALID_OPTION_TYPES or (o['type'] == 'silent' and o['id'] not in VALID_SILENT_OPTION_IDS):
                return False

        for i in self.images:
            if i['type'] not in VALID_IMAGE_TYPES:
                logging.info("Error in image type %s" % i['type'])
                return False
            #logging.info("Made it to the t loop")
            for t in VALID_IMAGE_TYPES:
                try:
                    #logging.info(i[t]['files'])
                    for f in i[t]['files']:
                        try:
                            #logging.info(f['patch']['type'])
                            if f['patch']['type'] not in VALID_PATCH_TYPES:
                                logging.info("Error in patch type %s" % f['patch']['type'])
                                return False
                        except TypeError:
                            continue
                except KeyError:
                    continue
        return True

    def _validate_patch_existence(self):
        for i in self.images:
            for t in VALID_IMAGE_TYPES:
                try:
                    for f in i[t]['files']:
                        try:
                            patch = f['patch']
                            try:
                                if patch['type'] == 'list':
                                    for p in list:
                                        patch_path = pathjoin(self.patch_dir, p)
                                        if not isfile(patch_path):
                                            return FileNotFoundError(patch_path)
                                elif patch['type'] == 'boolean':
                                    true_patch_path = pathjoin(self.patch_dir, patch['true'])
                                    if not isfile(true_patch_path):
                                        return FileNotFoundError(true_patch_path)
                                    false_patch_path = pathjoin(self.patch_dir, patch['false'])
                                    if not isfile(false_patch_path):
                                        return FileNotFoundError(false_patch_path)
                            except TypeError:
                                # Interprets "type" as a string index if it has no type field.
                                # This is the case for the normal generic patch.
                                patch_path = pathjoin(self.patch_dir, f['patch'])
                                if not isfile(patch_path):
                                    return FileNotFoundError(patch_path)
                        except KeyError:
                            continue
                except KeyError:
                    continue
        return True

def input_catch_keyboard_interrupt(prompt):
    try:
        result = input(prompt)
    except KeyboardInterrupt:
        exit_quietly()
    except EOFError:
        exit_quietly()
    return result

def exit_quietly():
    # Exit without the pyinstaller "Script failed to execute" message.
    try:
        sys.exit()
    except SystemExit:
        _exit(0)

def select_config():
    # Find the configs and choose one if necessary.
    configs = [pathjoin(exe_dir, f) for f in listdir(exe_dir) if f.startswith('Pachy98-') and f.endswith('.json')]
    if len(configs) == 0:
        message_wait_close('No "Pachy98-*.json" config files were found in this directory.')

    elif len(configs) > 1:
        print("Multiple Pachy98 json config files found. Which game do you want to patch?")
        for i, c in enumerate(configs):
            cfg = Config(c)
            print("%i) %s" % (i+1, cfg.info['game']))
        config_choice = 0
        while config_choice not in range(1, len(configs)+1):
            print("Enter a number %i-%i." % (1, len(configs)))
            try:
                config_choice = int(input_catch_keyboard_interrupt(">"))
            except ValueError:  # int() on a string: try again
                pass
        selected_config = configs[config_choice-1]
    else:
        selected_config = configs[0]
    return selected_config

def y_n_input():
    print('(y/n)')
    user_input = input_catch_keyboard_interrupt(">")

    user_input = user_input.strip(" ").lower()[0]
    while user_input not in ('y', 'n'):
        print('(y/n)')
        user_input = input_catch_keyboard_interrupt(">")
        user_input = user_input.strip(" ").lower()[0]

    return user_input

def message_wait_close(msg):
    print(msg)
    input("Press ENTER to close this patcher.")
    exit_quietly()

def except_handler(exc_type, exc_value, exc_traceback):
    logging.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

def patch_images(selected_images, cfg):
    backup_directory = pathjoin(exe_dir, 'backup')
    bin_dir = pathjoin(exe_dir, 'bin')

    for i, disk_path in enumerate(selected_images):
        image = cfg.images[i]
        disk_directory = pathsplit(disk_path)[0]
        DiskImage = Disk(disk_path, backup_folder=backup_directory, ndc_dir=bin_dir)

        if not access(disk_path, W_OK):
            message_wait_close('Can\'t access the file "%s". Make sure the file is not read-only.' % disk_path)

        print("Backing up %s to %s now..." % (disk_path, backup_directory))
        if stat(disk_path).st_size > 100000000:  # 100 MB+ disk images
            print("This is a large disk image, so it may take a few moments...")
        try:
            DiskImage.backup()
        except PermissionError:
            message_wait_close('Can\'t access the file "%s". Make sure the file is not in use.' % disk_path)

        if DiskImage.extension in HARD_DISK_FORMATS:
            files = image['hdd']['files']
        else:
            files = image['floppy']['files']

        # Find the right directory to look for the files in.
        disk_filenames = [f['name'] for f in files]

        path_in_disk = DiskImage.find_file_dir(disk_filenames)
        if path_in_disk is None:
            message_wait_close("Can\'t access the file '%s' now, but could before. Make sure it is not in use, and try again." % disk_path)

        for f in files:
            # Ignore files that lack a patch
            try:
                _ = f['patch']
            except KeyError:
                continue

            print('Extracting %s...' % f['name'])
            try:
                DiskImage.extract(f['name'], path_in_disk)
            except FileNotFoundError:
                print("Error. Restoring from backup...")
                DiskImage.restore_from_backup()
                message_wait_close("Couldn't access the disk. Make sure it is not open in EditDisk/ND, and try again.")
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
            for i, patch in enumerate(patch_list):
                patch_filepath = pathjoin(exe_dir, 'patch', patch)
                patchfile = Patch(extracted_file_path, patch_filepath, edited=extracted_file_path + '_edited', xdelta_dir=bin_dir)
                try:
                    print("Patching %s..." % f['name'])
                    patchfile.apply()
                    patch_worked = True
                except PatchChecksumError:
                    if i < len(patch_list) - 1:
                        print("Trying backup patch for %s..." % f['name'])

            if not patch_worked:
                print("Error. Restoring from backup...")
                DiskImage.restore_from_backup()
                remove(extracted_file_path)
                remove(extracted_file_path + '_edited')
                message_wait_close("Patch checksum error. This disk is not compatible with this patch, or is already patched.")

            copyfile(extracted_file_path + '_edited', extracted_file_path)
            if not options['delete_all_first']:
                print("Inserting %s..." % f['name'])
                try:
                    DiskImage.insert(extracted_file_path, path_in_disk)
                except ReadOnlyDiskError:
                    print("Error. Restoring from backup...")
                    DiskImage.restore_from_backup()
                    message_wait_close("Error inserting %s. Make sure the disk is not read-only or open in EditDisk/ND, and try again." % f['name'])
                remove(extracted_file_path)
                remove(extracted_file_path + '_edited')

        if options['delete_all_first']:
            for f in files:
                try:
                    print("Deleting %s..." % f['name'])
                    DiskImage.delete(f['name'], path_in_disk)
                except ReadOnlyDiskError:
                    print("Error. Restoring from backup...")
                    DiskImage.restore_from_backup()
                    message_wait_close("Error deleting", f, ". Make sure the disk is not read-only, and try again.")
            for f in files:
                extracted_file_path = pathjoin(disk_directory, f['name'])
                print("Inserting %s..." % f['name'])
                try:
                    DiskImage.insert(extracted_file_path, path_in_disk, delete_original=False)
                except ReadOnlyDiskError:
                    print("Error. Restoring from backup...")
                    DiskImage.restore_from_backup()
                    message_wait_close("Error inserting", f, ". Make sure the disk is not read-only or open in EditDisk/ND, and try again.")
                remove(extracted_file_path)
                remove(extracted_file_path + '_edited')


if __name__== '__main__':
    # Set the current directory to the magical pyinstaller folder if necessary.
    exe_dir = getcwd()
    if hasattr(sys, '_MEIPASS'):
        chdir(sys._MEIPASS)
        # All the stuff in the exe's dir should be prepended with this so it can be found.
        exe_dir = pathsplit(sys.executable)[0]
    bin_dir = pathjoin(exe_dir, 'bin')

    # Setup log
    logging.basicConfig(filename=pathjoin(exe_dir, 'pachy98-log.txt'), level=logging.INFO)
    sys.excepthook = except_handler
    logging.info("Log started")

    print("Pachy98 %s by 46 OkuMen" % VERSION)

    selected_config = select_config()
    config_path = pathjoin(exe_dir, selected_config)
    
    cfg = Config(config_path)
    
    print("Patching: %s (%s) %s by %s ( %s )" % (cfg.info['game'], cfg.info['language'], cfg.info['version'], cfg.info['author'], cfg.info['authorsite']))

    # Check for updates
    try:
        version_url = cfg.info['versionurl']
        print("\nChecking for updates to this translation... ", end="")
        site_version = urlopen(version_url).readline().decode('utf-8')
        site_version_int = int(site_version.replace('v', '').replace('.', ''))
        this_version_int = int(cfg.info['version'].replace('v', '').replace('.', ''))
        
        if site_version_int > this_version_int:
            print("\nThere is a new update (%s) available!" % site_version)
            print("Get it here: %s\n" % cfg.info['downloadurl'])
        else:
            print("It's up to date.\n")
    except KeyError:
        pass
    except HTTPError:
        print("\nCouldn't connect to the site. Proceeding with patching normally.\n")
    except ValueError:
        logging.info("This version URL contains something malformed: %s" % version_url)
        print("\nVersion url didn't contain a current version... Now patching normally.\n")
    # TODO: Need an exception for timeouts or other url errors.



    expected_image_length = len([i for i in cfg.images if i['type'] != 'disabled'])

    selected_images = [None,]*expected_image_length
    arg_images = []
    hd_found = False

    # ['pachy98.exe', 'arg1', 'arg2',] etc
    logging.info("CLI args are: %s" % sys.argv)
    if len(sys.argv) > 1:
        # Filenames have been provided as arguments.
        arg_images = sys.argv[1:]
        plausible_dir_path = pathjoin(exe_dir, arg_images[0])

    # Is there a single argument with a dir path?
    patch_plain_files = False
    plain_files_dir = '.'
    if len(arg_images) == 1 and isdir(plausible_dir_path):
        patch_plain_files = all([a in listdir(plausible_dir_path) for a in cfg.all_filenames])
        if patch_plain_files:
            plain_files_dir = plausible_dir_path

    # Ensure the arg images are in the right order by checking their contents.
    else:
        hdd_found = False
        for image in cfg.images:
            image_found = False
            if hdd_found:
                break

            for arg_image in arg_images:
                ArgDisk = Disk(arg_image, ndc_dir=bin_dir)
                if ArgDisk.find_file_dir(cfg.all_filenames):
                    selected_images = [arg_image,]
                    image_found = True
                    hdd_found = True

                if hdd_found:
                    break
                
                disk_filenames = [f['name'] for f in image['floppy']['files']]
                if ArgDisk.find_file_dir(disk_filenames):
                    selected_images[image['id']] = arg_image
                    image_found = True

            if not image_found:
                selected_images[image['id']] = None

    # Otherwise, search the directory for common image names
    # Only do this if you don't have a full set of selected_images or an HDI already from CLI args.
    if len([f for f in selected_images if f is not None]) < expected_image_length and len(selected_images) > 1 and not patch_plain_files:
        print("Looking for %s disk images in this directory..." % cfg.info['game'])
        abs_paths_in_dir = [pathjoin(exe_dir, f) for f in listdir(exe_dir)]
        #logging.info("files in exe_dir: %s" % listdir(exe_dir))
        image_paths_in_dir = [f for f in abs_paths_in_dir if is_valid_disk_image(f)]
        logging.info("images in exe_dir: %s" % image_paths_in_dir)
        disks_in_dir = [Disk(f, ndc_dir=bin_dir) for f in image_paths_in_dir]

        for image in cfg.images:
            if image['type'] == 'mixed':
                for d in disks_in_dir:
                    if d.find_file_dir(cfg.all_filenames) is not None:
                        selected_images = [d.filename,]
                        hd_found = True
                        break

                if not hd_found:
                    floppy_filenames = [f['name'] for f in image['floppy']['files']]
                    floppy_found = False
                    for d in disks_in_dir:
                        if d.find_file_dir(floppy_filenames) is not None:
                            selected_images[image['id']] = d.filename
                            floppy_found = True
                            break

                    if not floppy_found:
                        print("No disk found for '%s'" % image['name'])
                        selected_images[image['id']] = None

            elif image['type'] == 'floppy' and not hd_found:
                floppy_found = False
                floppy_filenames = [f['name'] for f in image['floppy']['files']]
                for d in disks_in_dir:

                    if d.find_file_dir(floppy_filenames) is not None:
                        selected_images[image['id']] = d.filename
                        floppy_found = True
                        break

                if not floppy_found:
                    print("No disk found for '%s'" % image['name'])
                    selected_images[image['id']] = None

    #if len(arg_images) > 0 and len([i for i in selected_images if i is not None]) != len(arg_images):
    #    print("The provided images weren't an entire game, so attempted to autodetect the rest.")

    if len([i for i in selected_images if i is not None]) not in (1, expected_image_length) and not patch_plain_files:
        # That was all futile. Last ditch effort: Look for the plain files in the dir and subdirs
        patch_plain_files = all([a in listdir(exe_dir) for a in cfg.all_filenames])
        if not patch_plain_files:
            # Also look in subdirs one deep.
            exe_subdirs = [s for s in listdir(exe_dir) if isdir(pathjoin(exe_dir, s)) and s not in ('backup', 'bin', 'patch')]
            logging.info("Looking in these one-deep subdirs: %s" % exe_subdirs)
            for subdir in exe_subdirs:
                patch_plain_files = all([a in listdir(pathjoin(exe_dir, subdir)) for a in cfg.all_filenames])
                if patch_plain_files:
                    plain_files_dir = subdir
                    print(subdir)
                    break

    if len([i for i in selected_images if i is not None]) not in (1, expected_image_length) and not patch_plain_files:
        print("Could not auto-detect all your disks. Close this and drag them all onto Pachy98.EXE, or enter the filenames manually here:")
        for image in cfg.images:
            if patch_plain_files:
                break
            if selected_images[image['id']] is None:
                filename = ''
                game_files_in_specified_file = False
                while not game_files_in_specified_file and not patch_plain_files:
                    filename = input_catch_keyboard_interrupt("%s filename:\n>" % image['name'])
                    filename = filename.strip('"')
                    filename = pathjoin(exe_dir, filename)
                    if isdir(filename):
                        subdir = filename
                        patch_plain_files = all([a in listdir(pathjoin(exe_dir, subdir)) for a in cfg.all_filenames])
                        if patch_plain_files:
                            plain_files_dir = subdir
                            break
                        else:
                            print("Folder doesn't contain the correct gamefiles.")
                    elif isfile(filename):
                        try:
                            d = Disk(filename, ndc_dir=bin_dir)
                            if d.find_file_dir(cfg.all_filenames):
                                game_files_in_specified_file = True
                            else:
                                print("Disk image doesn't contain the correct gamefiles, or is currently in use.")
                        except PermissionError:
                            print("File couldn't be accessed. Make sure it is not currently in use.")
                        except FileFormatNotSupportedError:
                            print("File is not a supported disk image.")
                    elif not isfile(filename):
                        print("File doesn't exist.")
                    elif not is_valid_disk_image(filename):
                        print("File is not a supported disk image type.")
                if not patch_plain_files:
                    selected_images[image['id']] = filename
                    if filename.split('.')[-1].lower() in HARD_DISK_FORMATS:
                        selected_images = [filename,]
                        break

    if not patch_plain_files:
        print("\nPatch these disk images?")
        if len(selected_images) == 1:
            print("%s: %s" % ("Game HDD", selected_images[0]))
        else:
            for image in cfg.images:
                print("%s: %s" % (image['name'], selected_images[image['id']]))
    else:
        print("\nPatch your gamefiles in the folder '%s' directly?" % plain_files_dir)
        print(cfg.all_filenames)

    confirmation = y_n_input()
    if confirmation.strip(" ".lower()[0]) == 'n':
        exit_quietly()

    # Get cfg.options related input from the user, then put them in the dict "options".
    # TODO: Could do this in the Config object instead.
    options = {}
    options['delete_all_first'] = False
    for o in cfg.options:
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

    backup_directory = pathjoin(exe_dir, 'backup')
    if not patch_plain_files:
        patch_images(selected_images, cfg=cfg)

    else:
        for f in cfg.hdd_files:
            # Ignore files without a patch
            try:
                _ = f['patch']
            except KeyError:
                continue

            f_path = pathjoin(exe_dir, plain_files_dir, f['name'])
            # Patch fhe files without doing any extracting stuff, but still consider options!
            print("Backing up %s..." % f['name'])
            copyfile(f_path, pathjoin(backup_directory, f['name']))
            copyfile(f_path, f['name'] + '_edited')
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
            for i, patch in enumerate(patch_list):
                patch_filepath = pathjoin(exe_dir, 'patch', patch)
                patchfile = Patch(f_path, patch_filepath, edited=f['name'] + '_edited', xdelta_dir=bin_dir)
                try:
                    print("Patching %s..." % f['name'])
                    patchfile.apply()
                    patch_worked = True
                except PatchChecksumError:
                    if i < len(patch_list):
                        print("Trying failsafe patch for %s..." % f['name'])

            if not patch_worked:
                remove(f['name'] + '_edited')
                message_wait_close("Patch checksum error. This file is not compatible with this patch, or is already patched.")

            try:
                copyfile(f['name'] + '_edited', f_path)
            except PermissionError:
                # TODO: Restore the previous files from backup.
                remove(f['name'] + '_edited')
                message_wait_close("Permission error. Make sure the file %s is not read-only or open somewhere." % f_path)
            remove(f['name'] + '_edited')

    message_wait_close("Patching complete! Read the README and enjoy the game.")
