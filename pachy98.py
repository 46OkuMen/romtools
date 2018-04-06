"""
    A command-line patching program for Japanese PC game disk images.
    Reads a json config file, looks for relevant disk images in
"""

from tqdm import tqdm
import sys
import filecmp
import logging
import json
import jsonschema
import semver
from os import (
    listdir,
    mkdir,
    walk,
    remove,
    getcwd,
    chdir,
    access,
    W_OK,
    stat,
    _exit,
)
from shutil import (
    copyfile,
    rmtree
)
from os.path import (
    isfile,
    isdir,
    split as pathsplit,
    join as pathjoin,
)
from disk import (
    Disk,
    HARD_DISK_FORMATS,
    is_valid_disk_image,
    ReadOnlyDiskError,
    FileNotFoundError,
    FileFormatNotSupportedError,
)
from patch import Patch, PatchChecksumError
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

VERSION = 'v0.20.0'

VALID_SILENT_OPTION_IDS = ['delete_all_first']
VALID_IMAGE_TYPES = ['floppy', 'hdd', 'mixed']


class Config:

    def __init__(self, json_path):
        self.SCHEMA = json.load(open('schema.json'))
        with open(json_path, 'r', encoding='utf-8') as f:
            unicode_safe = f.read()
        self.json = json.loads(unicode_safe)
        self.info = self.json['info']
        self.images = self.json['images']
        self.options = self.json.get('options', [])

        # Dicts are not a hashable type, so they need a list
        self.all_files = []
        self.all_filenames = set()
        self.new_files = []

        # Use this when searching through HDDs
        self.hdd_filenames = set()

        for i in self.images:
            try:
                floppy_files = i['floppy']['files']
                for ff in floppy_files:
                    try:
                        ff['new_file']
                        self.new_files.append(ff)
                    except KeyError:
                        self.all_files.append(ff)
                        self.all_filenames.add(ff['name'])
            except KeyError:
                hdd_files = i['hdd']['files']
                for hf in hdd_files:
                    try:
                        hf['new_file']
                        self.new_files.append(hf)
                    except KeyError:
                        self.all_files.append(hf)
                        self.all_filenames.add(hf['name'])
            try:
                hdd_files = i['hdd']['files']
                for hf in hdd_files:
                    self.hdd_filenames.add(hf['name'])
            except KeyError:
                pass

        self.all_filenames = list(self.all_filenames)
        self.hdd_filenames = list(self.hdd_filenames)

        self.patch_dir = pathjoin(pathsplit(json_path)[0], 'patch')

        # Validate with jsonschema.
        try:
            jsonschema.validate(self.json, self.SCHEMA)
        except jsonschema.ValidationError as e:
            message_wait_close("The config file %s is invalid: %s." % (json_path, e.message))

        if not self._validate_options():
            # TODO: Need a more specific message of what is wrong with it.
            message_wait_close("A config option in %s is not supported by "
                               "this verison of Pachy98. Download a newer "
                               "version." % json_path)
        try:
            self.__validate_patch_existence()
        except FileNotFoundError as e:
            message_wait_close("This config references a patch %s that doesn't exist." % e)

    def _validate_options(self):
        #try:
        #    jsonschema.validate(self.json, self.SCHEMA)
        #except jsonschema.ValidationError:
        #    print(jsonschema.ValidationError.message)
        #    return False

        for o in self.options:
            if (o['type'] == 'silent' and o['id'] not in
                    VALID_SILENT_OPTION_IDS):
                return False

        return True

    def __get_files(self, image):
        return image.get('files', [])

    def __validate_path(self, filename):
        path = pathjoin(self.patch_dir, filename)
        if not isfile(path):
            raise FileNotFoundError(path)

    def __validate_patch_existence(self):
        for image in self.images:
            floppy_image = image.get('floppy', {})
            hdd_image = image.get('hdd', {})
            files = (self.__get_files(floppy_image)
                     + self.__get_files(hdd_image))
            for f in files:
                patch = f.get('patch')
                if patch is None:
                    continue
                elif isinstance(patch, dict):
                    if patch['type'] == 'list':
                        for filename in list:
                            self.__validate_path(filename)
                    elif patch['type'] == 'boolean':
                        self.__validate_path(patch['true'])
                        self.__validate_path(patch['false'])
                else:
                    # Interprets "type" as a string index if it has no type
                    # field.  This is the case for the normal generic patch.
                    self.__validate_path(patch)
        return True


def generate_config(disks):
    # disks is a list of filenames: [o1, o2, p1, p2]. o is original, p is patched
    #  Need an even number of disks.
    if len(disks) % 2 != 0 or len(disks) < 2:
        message_wait_close("Usage: pachy98.exe -generate disk1-orig.fdi disk2-orig.fdi disk1-patched.fdi disk2-patched.fdi")

    for d in disks:
        if not isfile(d):
            message_wait_close("%s does not exist." % d)

    original_disks = disks[:len(disks)//2]
    patched_disks =  disks[len(disks)//2:]

    #print(original_disks)
    #print(patched_disks)

    project_name = pathsplit(original_disks[0])[-1].split('.')[0]

    config_filename = "Pachy98-" + project_name + ".json"

    config = {}
    config['info'] = {
        'game': project_name,
        'language': 'Ithkuil',
        'version': 'v0.0.0',
        'author': 'You',
        'authorsite': 'http://romhacking.net'
    }

    config['images'] = []


    for disk_index in range(len(disks)//2):
        o = original_disks[disk_index]
        disk = Disk(o)
        original_folder = pathsplit(o)[-1].split('.')[0] + "-original"
        mkdir(original_folder)
        files, dirs = disk.listdir('')
        for di in dirs:
            disk.extract(di, dest_path=original_folder)
        for f in files:
            disk.extract(f, dest_path=original_folder)

        p = patched_disks[disk_index]
        disk = Disk(p)
        patched_folder = pathsplit(p)[-1].split('.')[0] + "-patched"
        mkdir(patched_folder)
        files, dirs = disk.listdir('')
        for di in dirs:
            disk.extract(di, dest_path=patched_folder)
        for f in files:
            disk.extract(f, dest_path=patched_folder)

        patched_files = []

        for root, dirs, files in walk(original_folder):
            patched_root = root.replace(original_folder, patched_folder)
            for f in files:
                original_file = pathjoin(root, f)
                patched_file = pathjoin(patched_root, f)
                if not filecmp.cmp(original_file, patched_file, shallow=False):
                    #print(original_file, "is different from", patched_file)
                    patched_files.append(f)
                    patch_filename = f + '.xdelta'
                    if not isdir('patch'):
                        mkdir('patch')
                    patch_destination = pathjoin('patch', patch_filename)
                    filepatch = Patch(original_file, patch_destination, edited=patched_file)
                    filepatch.create()

        if disk.extension in HARD_DISK_FORMATS:
            disk_type = 'hdd'
        else:
            disk_type = 'floppy'

        file_field = []
        for f in patched_files:
            file_field.append({
                    'name': f,
                    'patch': f + '.xdelta'
                })

        config['images'].append({
                'name': 'Disk %s' % disk_index,
                'id': disk_index,
                'type': disk_type,
            })

        config['images'][disk_index][disk_type] = {
            'files': file_field
        }

        # Cleanup
        rmtree(original_folder)
        rmtree(patched_folder)

    with open(config_filename, 'w') as f:
        json.dump(config, f, indent=2)


def input_catch_keyboard_interrupt(prompt):
    try:
        result = input(prompt)
    except KeyboardInterrupt:
        exit_quietly()
    except EOFError:
        exit_quietly()
    return result


def check_for_update(local_version, remote_version_url):
    if not (local_version and remote_version_url):
        return
    try:
        print("Checking for updates to this translation... ", end="")
        remote_version = (urlopen(remote_version_url)
                          .readline().decode('utf-8'))

        if semver.compare(local_version[1:], remote_version) == -1:
            print("There is a new update (%s) available!" % remote_version)
            print("Get it here: %s" % cfg.info['downloadurl'])
        else:
            print("It's up to date.\n")
    except (HTTPError, URLError):
        print("Couldn't connect to the site. "
              "Proceeding with patching normally.")
    except ValueError:
        print("Invalid version: %s" % remote_version)


def exit_quietly():
    # Exit without the pyinstaller "Script failed to execute" message.
    try:
        sys.exit()
    except SystemExit:
        _exit(0)


def select_config():
    # Find the configs and choose one if necessary.
    configs = [
        pathjoin(exe_dir, f)
        for f in listdir(exe_dir)
        if f.startswith('Pachy98-') and f.endswith('.json')
    ]
    good_configs = []
    for c in configs:
        try:
            Config(c)
            good_configs.append(c)
        except json.decoder.JSONDecodeError:
            logging.info("Config %s is invalid, and was skipped" % c)

    if len(good_configs) == 0:
        message_wait_close('No "Pachy98-*.json" config files were found in this directory.')

    elif len(good_configs) == 1:
        selected_config = good_configs[0]

    elif len(configs) > 1:
        print("Multiple Pachy98 json config files found. "
              "Which game do you want to patch?")
        for i, c in enumerate(good_configs):
            cfg = Config(c)
            print("%i) %s" % (i + 1, cfg.info['game']))
        config_choice = 0
        while config_choice not in range(1, len(good_configs) + 1):
            print("Enter a number %i-%i." % (1, len(good_configs)))
            try:
                config_choice = int(input_catch_keyboard_interrupt(">"))
            except ValueError:  # int() on a string: try again
                pass
        selected_config = good_configs[config_choice - 1]
    return selected_config


def y_n_input():
    print('(y/n)')
    try:
        user_input = input_catch_keyboard_interrupt(">")
    except IndexError:
        user_input = ""

    while user_input not in ('y', 'n'):
        print('(y/n)')
        user_input = input_catch_keyboard_interrupt(">")
        user_input = user_input.strip(" ").lower()
        try:
            user_input = user_input[0]
        except IndexError:
            user_input = ""

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


def patch_image(id, image):
    pass


def patch_images(selected_images, cfg):
    backup_directory = pathjoin(exe_dir, 'backup')
    bin_dir = pathjoin(exe_dir, 'bin')

    for i, disk_path in enumerate(selected_images):
        image = cfg.images[i]
        disk_directory = pathsplit(disk_path)[0]
        DiskImage = Disk(disk_path, backup_folder=backup_directory,
                         ndc_dir=bin_dir)

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

        for f in files:
            # Ignore files that lack a patch
            try:
                f['patch']
            except KeyError:
                continue

            print('Extracting %s...' % f['name'])
            paths_in_disk = DiskImage.find_file(f['name'])
            patch_worked = False
            for j, path_in_disk in enumerate(paths_in_disk):
                if patch_worked:
                    break

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
                            patch_list = [f['patch']['true']]
                        else:
                            patch_list = [f['patch']['false']]
                else:
                    patch_list = [f['patch']]

                # patch_worked = False
                for i, patch in enumerate(patch_list):
                    patch_filepath = pathjoin(exe_dir, 'patch', patch)
                    patchfile = Patch(
                        extracted_file_path,
                        patch_filepath,
                        edited=extracted_file_path + '_edited',
                        xdelta_dir=bin_dir)
                    try:
                        print("Patching %s..." % f['name'])
                        patchfile.apply()
                        patch_worked = True
                    except PatchChecksumError:
                        if i < len(patch_list) - 1:
                            print("Trying backup patch for %s..." % f['name'])
                if not patch_worked and j < len(paths_in_disk) - 1:
                    print("Trying another file with the name %s..." % f['name'])

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
                    message_wait_close("Error deleting %s. Make sure the disk is not read-only, and try again.")
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

        for f in cfg.new_files:
            new_file_path = pathjoin(exe_dir, 'patch', f['name'])
            print("Inserting new file %s..." % f['name'])
            DiskImage.insert(new_file_path, path_in_disk, delete_original=False)


if __name__ == '__main__':

    # Check args for a json-generating command
    if len(sys.argv) > 1:
        if sys.argv[1] == "-generate":
            generate_config(sys.argv[2:])
            message_wait_close("")

    # Set the current directory to the magical pyinstaller folder if necessary.
    exe_dir = getcwd()
    if hasattr(sys, '_MEIPASS'):
        chdir(sys._MEIPASS)
        # All the stuff in the exe's dir should be prepended with this so it can be found.
        exe_dir = pathsplit(sys.executable)[0]
    bin_dir = pathjoin(exe_dir, 'bin')

    # Setup log
    logging.basicConfig(filename=pathjoin(exe_dir, 'pachy98-log.txt'),
                        level=logging.INFO)
   # sys.excepthook = except_handler
    logging.info("Log started")

    print("Pachy98 %s by 46 OkuMen" % VERSION)

    selected_config = select_config()
    config_path = pathjoin(exe_dir, selected_config)

    cfg = Config(config_path)

    print("Patching: %s (%s) %s by %s ( %s )" %
          (cfg.info['game'], cfg.info['language'], cfg.info['version'],
           cfg.info['author'], cfg.info['authorsite']))

    check_for_update(cfg.info.get('version'), cfg.info.get('versionurl'))

    expected_image_length = len([i for i in cfg.images
                                 if i['type'] != 'disabled'])

    selected_images = [None] * expected_image_length
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
                # if ArgDisk.find_file_dir(cfg.all_filenames):
                if all([ArgDisk.find_file(filename) for filename in cfg.all_filenames]):
                    selected_images = [arg_image]
                    image_found = True
                    hdd_found = True

                if hdd_found:
                    break

                disk_filenames = [f['name'] for f in image['floppy']['files']]
                # if ArgDisk.find_file_dir(disk_filenames):
                if all([ArgDisk.find_file(filename) for filename in disk_filenames]):
                    selected_images[image['id']] = arg_image
                    image_found = True

            if not image_found:
                selected_images[image['id']] = None

    # Otherwise, search the directory
    # Only do this if you don't have a full set of selected_images or an HDI
    # already from CLI args.
    if selected_images == [
            None
    ] or (len([f for f in selected_images
               if f is not None]) < expected_image_length
          and len(selected_images) > 1 and not patch_plain_files):
        #print("Looking for %s disk images in this directory..." % cfg.info['game'])
        abs_paths_in_dir = [pathjoin(exe_dir, f) for f in listdir(exe_dir)]
        logging.info("files in exe_dir: %s" % listdir(exe_dir))
        image_paths_in_dir = [f for f in abs_paths_in_dir if is_valid_disk_image(f)]
        logging.info("images in exe_dir: %s" % image_paths_in_dir)
        disks_in_dir = [Disk(f, ndc_dir=bin_dir) for f in image_paths_in_dir]

        for image in cfg.images:
            logging.info("Looking for these files: %s" % cfg.hdd_filenames)
            if image['type'] == 'mixed' or image['type'] == 'hdd':
                for d in disks_in_dir:
                    #print("Looking through %s now for these files: %s" % (d, cfg.hdd_filenames))
                    if all([d.find_file(filename) for filename in cfg.hdd_filenames]):
                        selected_images = [d.filename]
                        hd_found = True
                        break

                if not hd_found:
                    floppy_found = False
                    try:
                        #print("No HD found, looking through %s now for %s." % (d, [f['name'] for f in image['floppy']['files']]))
                        floppy_filenames = [f['name'] for f in image['floppy']['files']]
                        for d in disks_in_dir:
                            #print("Trying disk %s" % d)
                            if all([d.find_file(filename) for filename in floppy_filenames]):
                                selected_images[image['id']] = d.filename
                                floppy_found = True
                                break
                    except KeyError:
                        pass

                    if not floppy_found:
                        print("No disk found for '%s'" % image['name'])
                        selected_images[image['id']] = None

            elif image['type'] == 'floppy' and not hd_found:
                floppy_found = False
                floppy_filenames = [f['name'] for f in image['floppy']['files']]
                for d in disks_in_dir:
                    if all([d.find_file(filename) for filename in floppy_filenames]):
                        selected_images[image['id']] = d.filename
                        floppy_found = True
                        break

                if not floppy_found:
                    print("No disk found for '%s'" % image['name'])
                    selected_images[image['id']] = None

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
                            if all([d.find_file(filename) for filename in cfg.all_filenames]):
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

    # Get cfg.options related input from the user, then put them in the dict
    # "options".
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
        for f in cfg.all_files:
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
                        patch_list = [f['patch']['true']]
                    else:
                        patch_list = [f['patch']['false']]
            else:
                patch_list = [f['patch']]

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
