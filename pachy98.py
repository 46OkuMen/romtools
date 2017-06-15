import sys, logging, json
from os import curdir, listdir, remove, getcwd, chdir, access, W_OK, stat
from shutil import copyfile
from os.path import isfile
from os.path import split as pathsplit
from os.path import join as pathjoin
from disk import Disk, HARD_DISK_FORMATS, SUPPORTED_FILE_FORMATS, ReadOnlyDiskError, FileNotFoundError, is_DIP
from patch import Patch, PatchChecksumError

VERSION = 'v0.7.0'

VALID_OPTION_TYPES = ['boolean', 'silent']
VALID_SILENT_OPTION_IDS = ['delete_all_first']
VALID_IMAGE_TYPES = ['floppy', 'hdd', 'mixed']
VALID_PATCH_TYPES = ['boolean', 'failsafelist']

def is_valid_disk_image(filename):
    logging.info("Checking is_valid_disk_image on %s" % filename)
    just_filename = pathsplit(filename)[1]
    if just_filename.lower().split('.')[-1] in SUPPORTED_FILE_FORMATS:
        return True
    elif len(just_filename.split('.')) == 1:
        logging.info("just_filename.lower().split('.') length is 1. trying is_DIP now")
        return is_DIP(filename)

def validate_config(cfg):
    for o in cfg['options']:
        if o['type'] not in VALID_OPTION_TYPES or (o['type'] == 'silent' and o['id'] not in VALID_SILENT_OPTION_IDS):
            return False

    for i in cfg['images']:
        if i['type'] not in VALID_IMAGE_TYPES:
            logging.info("Error in image type %s" % i['type'])
            return False
        logging.info("Made it to the t loop")
        for t in VALID_IMAGE_TYPES:
            try:
                logging.info(i[t]['files'])
                for f in i[t]['files']:
                    try:
                        logging.info(f['patch']['type'])
                        if f['patch']['type'] not in VALID_PATCH_TYPES:
                            logging.info("Error in patch type %s" % f['patch']['type'])
                            return False
                    except TypeError:
                        continue
            except KeyError:
                continue
    return True
                

def y_n_input():
    print('(y/n)')
    user_input = input(">")
    user_input = user_input.strip(" ").lower()[0]
    while user_input not in ('y', 'n'):
        print('(y/n)')
        user_input = input(">")
        user_input = user_input.strip(" ").lower()[0]

    return user_input

def message_wait_close(msg):
    print(msg)
    input("Press ENTER to close this patcher.")
    sys.exit()

def except_handler(type, value, tb):
    logging.exception("Uncaught exception: {0}".format(str(value)))


if __name__== '__main__':
    # Set the current directory to the magical pyinstaller folder if necessary.
    exe_dir = getcwd()
    print(exe_dir)
    if hasattr(sys, '_MEIPASS'):
        chdir(sys._MEIPASS)
        # All the stuff in the exe's dir should be prepended with this so it can be found.
        exe_dir = pathsplit(sys.executable)[0]
        bin_dir = pathjoin(exe_dir, 'bin')
    else:
        bin_dir = pathjoin(exe_dir, 'bin')

    # Setup log
    logging.basicConfig(filename=pathjoin(exe_dir, 'pachy98-log.txt'), level=logging.INFO)
    sys.excepthook = except_handler
    logging.info("Log started")

    print("Pachy98 %s by 46 OkuMen" % VERSION)

    # Find the configs and choose one if necessary.
    configs = [pathjoin(exe_dir, f) for f in listdir(exe_dir) if f.startswith('Pachy98-') and f.endswith('.json')]
    if len(configs) == 0:
        message_wait_close('No "Pachy98-*.json" config files were found in this directory.')

    elif len(configs) > 1:
        print("Multiple Pachy98 json config files found. Which game do you want to patch?")
        for i, c in enumerate(configs):
            with open(c, 'r', encoding='utf-8') as f:
                unicode_safe = f.read()
                cfg = json.loads(unicode_safe)
                print("%i) %s" % (i+1, cfg['info']['game']))
        config_choice = 0
        while config_choice not in range(1, len(configs)+1):
            print("Enter a number %i-%i." % (1, len(configs)))
            try:
                config_choice = int(input(">"))
            except ValueError:  # int() on a string: try again
                pass
        selected_config = configs[config_choice-1]
    else:
        selected_config = configs[0]
    
    config_path = pathjoin(exe_dir, selected_config)
    with open(config_path, 'r', encoding='utf-8') as f:
        unicode_safe = f.read()
    cfg = json.loads(unicode_safe)

    if not validate_config(cfg):
        message_wait_close("A config option in %s is not supported by this verison of Pachy98. Download a newer version." % selected_config)
    
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
    hdd_found = False
    for image in cfg['images']:
        image_found = False
        if hdd_found:
            break

        for arg_image in arg_images:
            ArgDisk = Disk(arg_image, ndc_dir=bin_dir)
            try:
                path_keywords = image['hdd']['path_keywords']
            except KeyError:
                path_keywords = []

            try:
                logging.info("Checking if it's a HDD now")
                disk_filenames = [f['name'] for f in image['hdd']['files']]
                if ArgDisk.find_file_dir(disk_filenames):
                    selected_images = [arg_image,]
                    image_found = True
                    hdd_found = True
                    logging.info("It's an HDD")
            except KeyError:
                pass

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
    if len([f for f in selected_images if f is not None]) < expected_image_length and len(selected_images) > 1:
        print("Looking for %s disk images in this directory..." % info['game'])
        abs_paths_in_dir = [pathjoin(exe_dir, f) for f in listdir(exe_dir)]
        logging.info("files in exe_dir: %s" % listdir(exe_dir))
        image_paths_in_dir = [f for f in abs_paths_in_dir if is_valid_disk_image(f)]
        logging.info("images in exe_dir: %s" % image_paths_in_dir)
        disks_in_dir = [Disk(f, ndc_dir=bin_dir) for f in image_paths_in_dir]

        for image in cfg['images']:
            if image['type'] == 'mixed':
                hdd_filenames = [f['name'] for f in image['hdd']['files']]
                try:
                    path_keywords = image['hdd']['path_keywords']
                except KeyError:
                    path_keywords = []
                for d in disks_in_dir:
                    if d.find_file_dir(hdd_filenames) is not None:
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

    if len(arg_images) > 0 and len([i for i in selected_images if i is not None]) != len(arg_images):
        print("The provided images weren't an entire game, so attempted to autodetect the rest.")

    if len([i for i in selected_images if i is not None]) not in (1, expected_image_length):
        print("Could not auto-detect all your disks. Close this and drag them all onto Pachy98.EXE, or enter the filenames manually here:")
        for image in cfg['images']:
            if selected_images[image['id']] is None:
                filename = ''
                while not isfile(filename) or not is_valid_disk_image(filename):
                    filename = input("%s filename:\n>" % image['name'])
                    filename = pathjoin(exe_dir, filename)
                    if not isfile(filename):
                        print("File doesn't exist.")
                    elif not is_valid_disk_image(filename):
                        print("File is not a supported disk image type.")
                selected_images[image['id']] = filename
                if filename.split('.')[-1].lower() in HARD_DISK_FORMATS:
                    selected_images = [filename,]
                    break

    print("\nPatch these disk images?")
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
        backup_directory = pathjoin(exe_dir, 'backup')
        DiskImage = Disk(disk_path, backup_folder=backup_directory, ndc_dir=bin_dir)

        if not access(disk_path, W_OK):
            message_wait_close('Can\'t access the file "%s". Make sure the file is not read-only.' % cfg['images'][i]['name'])

        print("Backing up %s to %s now..." % (disk_path, backup_directory))
        DiskImage.backup()

        if DiskImage.extension in HARD_DISK_FORMATS:
            files = image['hdd']['files']
        else:
            files = image['floppy']['files']

        # Find the right directory to look for the files in.
        disk_filenames = [f['name'] for f in files]
        try:
            keywords = image['hdd']['path_keywords']
        except KeyError:
            keywords = []
        print("Scanning %s for %s files now..." % (pathsplit(disk_path)[1], info['game']))
        if stat(disk_path).st_size > 100000000:
            print("This is a large disk image, so it may take a few moments...")

        path_in_disk = DiskImage.find_file_dir(disk_filenames)
        print(path_in_disk)

        for f in files:
            print('Extracting %s...' % f['name'])
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
                    continue

            if not patch_worked:
                DiskImage.restore_from_backup()
                remove(extracted_file_path)
                remove(extracted_file_path + '_edited')
                message_wait_close("Patch checksum error. This disk is not compatible with this patch, or is already patched.")

            copyfile(extracted_file_path + '_edited', extracted_file_path)
            if not options['delete_all_first']:
                print("Inserting %s..." % f['name'])
                DiskImage.insert(extracted_file_path, path_in_disk)
                remove(extracted_file_path)
                remove(extracted_file_path + '_edited')

        if options['delete_all_first']:
            for f in files:
                try:
                    print("Deleting %s..." % f['name'])
                    DiskImage.delete(f['name'], path_in_disk)
                except ReadOnlyDiskError:
                    DiskImage.restore_from_backup()
                    message_wait_close("Error deleting", f, ". Make sure the disk is not read-only, and try again.")
            for f in files:
                extracted_file_path = pathjoin(disk_directory, f['name'])
                print("Inserting %s..." % f['name'])
                DiskImage.insert(extracted_file_path, path_in_disk, delete_original=False)
                remove(extracted_file_path)
                remove(extracted_file_path + '_edited')
    message_wait_close("Patching complete! Read the README and enjoy the game.")


# Changes made to the json:
# Removed all 'disabled' disks
# Could probably get rid of "value" as well
# Can get rid of 'common' in each image.
