import xlsxwriter
from collections import OrderedDict
from openpyxl import load_workbook

SPECIAL_CHARACTERS = {
    'ō': '[o]',
    'Ō': '[O]',
    'ū': '[u]',
    '\uff0d': '\u30fc'   # Katakana long dash mark fix
}

def unpack(s, t=None):
    if t is None:
        t = str(s)[2:]
        s = str(s)[0:2]
    s = int(s, 16)
    t = int(t, 16)
    value = (t * 0x100) + s
    return value


def pack(h):
    s = h % 0x100
    t = h // 0x100
    return (s, t)


def ascii_to_hex_string(eng, control_codes={}):
    """Returns a hex string of the ascii bytes of a given english string."""
    eng_bytestring = ""
    if not eng:
        return ""
    else:
        try:
            eng = str(eng)
        except UnicodeEncodeError:
            # Tried to encode a fullwidth number. Encode it as sjis instead.
            eng = eng.encode('shift-jis')

        eng_bytestring = eng

        for cc in control_codes:
            cc_hex = ascii_to_hex_string(cc)
            if cc_hex in eng_bytestring:
                eng_bytestring = eng_bytestring.replace(cc_hex, control_codes[cc])

        return eng_bytestring


def sjis_to_hex_string(jp, control_codes={}):
    """Returns a hex string of the Shift JIS bytes of a given japanese string."""
    jp_bytestring = ""
    try:
        sjis = jp.encode('shift-jis')
    except AttributeError:
        # Trying to encode numbers throws an attribute error; they aren't important, so just keep the number
        sjis = str(jp)

    jp_bytestring = sjis

    for cc in control_codes:
        cc_hex = sjis_to_hex_string(cc)
        if cc_hex in jp_bytestring:
            jp_bytestring = jp_bytestring.replace(cc_hex, control_codes[cc])

    return jp_bytestring


class Translation(object):
    """Has an offset, a SJIS japanese string, and an ASCII english string."""
    def __init__(self, gamefile, location, japanese, english, category=None, portrait=None, cd_location=None, control_codes={}):
        self.location = location
        self.cd_location = cd_location
        self.gamefile = gamefile
        self.japanese = japanese
        self.english = english

        self.jp_bytestring = japanese
        self.en_bytestring = english

        self.category = category
        self.portrait = portrait

        for cc in control_codes:
            if cc in self.jp_bytestring:
                self.jp_bytestring = self.jp_bytestring.replace(cc, control_codes[cc])
            if cc in self.en_bytestring:
                self.en_bytestring = self.en_bytestring.replace(cc, control_codes[cc])


    def refresh_jp_bytestring(self):
        self.jp_bytestring = sjis_to_hex_string(self.japanese)
        return self.jp_bytestring

    def refresh_en_bytestring(self):
        self.en_bytestring = ascii_to_hex_string(self.english)
        return self.en_bytestring

    def __repr__(self):
        return "%s %s" % (hex(self.location), self.english)


class BorlandPointer(object):
    """Two-byte, little-endian pointer with a constant added to retrieve location."""
    def __init__(self, gamefile, pointer_location, text_location):
        # A BorlandPointer has only one location. The container OrderDicts have lists of pointers,
        # each having their own location.
        self.gamefile = gamefile
        self.constant = self.gamefile.pointer_constant
        self.location = pointer_location
        self.text_location = text_location
        self.new_text_location = text_location

    def text(self):
        gamefile_slice = self.gamefile.filestring[self.text_location:self.text_location+30]
        gamefile_slice = gamefile_slice.split(b'\x00')[0]
        try:
            gamefile_slice = gamefile_slice.decode('shift_jis')
        except:
            gamefile_slice = "weird bytes"
        return gamefile_slice

    def original_text(self):
        gamefile_slice = self.gamefile.original_filestring[self.text_location:self.text_location+45]
        gamefile_slice = gamefile_slice.split('\x00')[0]
        try:
            gamefile_slice = gamefile_slice.decode('shift_jis')
        except:
            gamefile_slice = "weird bytes"
        return gamefile_slice

    def move_pointer_location(self, diff):
        self.location += diff
        return self.location


    def edit(self, diff):
        print("Editing %s with diff %s" % (self, diff))
        first = hex(self.gamefile.filestring[self.location])
        second = hex(self.gamefile.filestring[self.location+1])
        #print(first, second)
        old_value = unpack(first, second)
        new_value = old_value + diff

        #print(hex(old_value))
        #print(diff)

        new_bytes = new_value.to_bytes(length=2, byteorder='little')
        #print(hex(old_value), hex(new_value))
        #print((first, second), repr(new_bytes))
        #new_first, new_second = bytearray(new_bytes[0]), bytearray(new_bytes[1])
        prefix = self.gamefile.filestring[:self.location]
        suffix = self.gamefile.filestring[self.location+2:]
        self.gamefile.filestring = prefix + new_bytes + suffix
        self.new_text_location = new_value
        #assert len(self.gamefile.filestring) == len(self.gamefile.original_filestring), (hex(len(self.gamefile.filestring)), hex(len(self.gamefile.original_filestring)))
        return new_bytes

    def __repr__(self):
        return "%s pointing to %s" % (hex(self.location), hex(self.new_text_location))


class DumpExcel(object):
    """
    Takes a dump excel path, and lets you get a block's translations from it.
    """
    # TODO: Currently uses the order of the excel sheet. Might want to sort it by text_location in get_translations()...

    def __init__(self, path, control_codes={}):
        self.path = path
        self.workbook = load_workbook(self.path)
        self.control_codes = control_codes

        #self.rows_with_file = {}
        #print("About to cache rows with file")
        #self._cache_rows_with_file()


    def get_translations(self, target, sheet_name=None, include_blank=False, use_cd_location=False):
        """Get the translations for a file."""
        # Accepts a block, gamefile, or filename as "target".
        # If sheet_name is defined, the target will be the filenamne within that multi-file sheet.
        trans = []    # translations[offset] = Translation()

        if sheet_name:
            worksheet = self.workbook.get_sheet_by_name(sheet_name)
        else:
            try:
                worksheet = self.workbook.get_sheet_by_name(target.gamefile.filename)
            except KeyError:
                worksheet = self.workbook.get_sheet_by_name(target.gamefile.filename.lstrip('decompressed_').rstrip('.decompressed'))
            except AttributeError:
                try:
                    worksheet = self.workbook.get_sheet_by_name(target.filename)
                except AttributeError:
                    worksheet = self.workbook.get_sheet_by_name(target)

        first_row = list(worksheet.rows)[0]
        header_values = [t.value for t in first_row]

        try:
            offset_col = header_values.index('Offset (FD)')
            cd_offset_col = header_values.index('Offset (CD)')
        except ValueError:
            offset_col = header_values.index('Offset')
            cd_offset_col = None

        jp_col = header_values.index('Japanese')

        # Appareden (and later games) have two (three?) English columns
        try:
            en_col = header_values.index('English (Typeset)')
        except ValueError:
            try:
                en_col = header_values.index('English (Ingame)')
            except ValueError:
                en_col = header_values.index('English')

        try:
            filename_col = header_values.index('File')
        except ValueError:
            filename_col = None

        # TODO: These more ad-hoc columns might do better in a dictionary or something.

        try:
            category_col = header_values.index('Category')
        except ValueError:
            category_col = None

        try:
            portrait_col = header_values.index('Portrait')
        except ValueError:
            portrait_col = None


        for row in list(worksheet.rows)[1:]:  # Skip the first row, it's just labels

            # Skip rows that aren't for this file, if a sheet name is specified
            if sheet_name and row[filename_col].value != target:
                continue

            try:
                offset = int(row[offset_col].value, 16)
            except TypeError:
                # Either a blank line or a total value. Ignore it.
                offset = None

            try:
                cd_offset = int(row[cd_offset_col].value, 16)
            except TypeError:
                cd_offset = None

            if offset is None and cd_offset is None:
                break

            try:
                start, stop = target.start, target.stop
                if use_cd_location:
                    offset = cd_offset
                if offset is None:
                    continue
                if not (target.start <= offset < target.stop):
                    continue
            except AttributeError:
                pass

            if row[en_col].value is None and not include_blank:
                continue
            #print(sheet_name)
            japanese = row[jp_col].value.encode('shift-jis')
            #print(japanese)
            #print(row[en_col].value)
            if row[en_col].value is None:
                english = b""
            else:
                try:
                    english = row[en_col].value.encode('shift-jis')
                except AttributeError:   # Int column values
                    english = str(row[en_col].value).encode('shift-jis')
                except UnicodeEncodeError:

                    english = row[en_col].value
                    for ch in SPECIAL_CHARACTERS:
                        english = english.replace(ch, SPECIAL_CHARACTERS[ch])
                    english = english.encode('shift-jis')

            if category_col is not None:
                category = row[category_col].value
            else:
                category = None

            if portrait_col is not None:
                portrait = row[portrait_col].value
            else:
                portrait = None


            # if isinstance(japanese, long):
            #    # Causes some encoding problems? Trying to skip them for now
            #    continue

            # Blank strings are None (non-iterable), so use "" instead.
            if not english:
                english = b""

            trans.append(Translation(target, offset, japanese, english, category=category, portrait=portrait, control_codes=self.control_codes, cd_location=cd_offset))
        return trans


class PointerExcel(object):
    def __init__(self, path):
        self.path = path
        try:
            self.workbook = load_workbook(self.path)
        except IOError:
            self.workbook = xlsxwriter.Workbook(self.path)

    def add_worksheet(self, title):
        self.worksheet = self.workbook.add_worksheet(title)
        sheet_format = {'bold': True,
                        'align': 'center',
                        'bottom': True,
                        'bg_color': 'gray'}
        header = self.workbook.add_format(sheet_format)
        self.worksheet.write(0, 0, 'Text Loc', header)
        self.worksheet.write(0, 1, 'Ptr Loc', header)
        self.worksheet.write(0, 2, 'Points To', header)
        self.worksheet.write(0, 3, 'Comments', header)
        self.worksheet.set_column('A:A', 7)
        self.worksheet.set_column('B:B', 7)
        self.worksheet.set_column('C:C', 30)
        self.worksheet.set_column('D:D', 30)
        return self.worksheet

    def get_pointers(self, gamefile, pointer_sheet_name):
        pointers = OrderedDict()
        try:
            ws = self.workbook[pointer_sheet_name]
        except KeyError:
            # Sheet does not exist. Return an empty pointers list.
            return pointers

        for i, row in enumerate(ws):
            if i == 0:
                continue
            text_location = int(row[0].value, 16)
            try:
                pointer_location = int(row[1].value, 16)
            except ValueError:
                print("Pointer with text location %s had no pointer location. Proceed with caution" % hex(text_location))
                continue
            ptr = BorlandPointer(gamefile, pointer_location, text_location)
            if text_location in pointers:
                pointers[text_location].append(ptr)
            else:
                pointers[text_location] = [ptr, ]
        return pointers

    def close(self):
        self.workbook.close()
"""
class DumpGoogleSheet(object):
"""
       # A dump in a Google Sheet, with methods to update various columns
"""
    def __init__(self, filename):
        gc = pygsheets.authorize(outh_file='client_secret_1010652634407-2d4gjkn44a5020jg6tl4hqjld1130fjs.apps.googleusercontent.com.json', no_cache=True)
        self.workbook = gc.open(filename)

def update_google_sheets(local_filename, google_filename):
    local = DumpExcel(local_filename)
    google = DumpGoogleSheet(google_filename)

    for name in local.workbook.get_sheet_names():
        local_worksheet = local.workbook.get_sheet_by_name(name)

        first_row = list(local_worksheet.rows)[0]
        header_values = [t.value for t in first_row]

        offset_col = header_values.index('Offset')
        jp_col = header_values.index('Japanese')
        # TODO: Probably want to update these too

        original_en_col = header_values.index('English (kuoushi)')
        ingame_en_col = header_values.index('English (Ingame)')

        google_worksheet = google.workbook.worksheet_by_title(name)

        google_values = google_worksheet.get_all_values(returnas='cell', include_empty=False)


        #print(google_values)

        # TODO: Propagate a deleted row from local to Google sheet; not supported yet

        # TODO: Sys dump has one less row in google sheet than local, but msg dump has same row count!
        print(len(google_values)-1, local_worksheet.max_row)
        assert len(google_values)-1 <= local_worksheet.max_row, "Row has been deleted, update manually"
        if len(google_values)-1 < local_worksheet.max_row:
            print("Row added to local sheet, inserting that in google sheet")
            for i, row in enumerate(local_worksheet):
                google_offset = google_values[i][0].value
                local_offset = row[0].value
                if google_offset != local_offset:
                    vals_list = [cell.value for cell in row]
                    for cell_i in range(len(vals_list)):
                        if vals_list[cell_i] is None:
                            vals_list[cell_i] = ''
                    google_worksheet.insert_rows(row=i, number=1, values=vals_list)


        # TODO: Want to update each direction separately...
        for en_col in (original_en_col, ingame_en_col):

            for i, row in enumerate(local_worksheet):
                try:
                    google_val = google_values[i][en_col].value
                except IndexError:
                    # Likely to be a sheet that doesn't have any values
                    print("Skipping this sheet")
                    break
                local_val = row[en_col].value

                if google_val is None:
                    google_val = ''
                if local_val is None:
                    local_val = ''

                #print(repr(google_val), repr(local_val))

                if str(google_val) != str(local_val):
                    # If ingame col is different, sync local changes to google sheet
                    if en_col == ingame_en_col:
                        label = google_values[i][en_col].label
                        google_worksheet.update_cell(label, local_val)
                    # If the kuoushi col has changed, sync google changes to local sheet
                    elif en_col == original_en_col:
                        cell = local_worksheet.cell(row=i+1, column=en_col+1)
                        cell.value = google_val

    local.workbook.save(local_filename)
"""