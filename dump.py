from openpyxl import Workbook, load_workbook

def ascii_to_hex_string(eng, control_codes={}):
    """Returns a hex string of the ascii bytes of a given english (translated) string."""
    eng_bytestring = ""
    if not eng:
        return ""
    else:
        try:
            eng = str(eng)
        except UnicodeEncodeError:
            # Tried to encode a fullwidth number. Encode it as sjis instead.
            eng = eng.encode('shift-jis')
        #for char in eng:
        #   eng_bytestring += "\x" + "%02x" % ord(char)

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
    def __init__(self, block, location, japanese, english):
        self.location = location
        self.block = block
        self.japanese = japanese
        self.english = english

        self.jp_bytestring = sjis_to_hex_string(japanese)
        self.en_bytestring = ascii_to_hex_string(english)

    def __repr__(self):
        return self.english


class BorlandPointer(object):
    """Two-byte, little-endian pointer with a constant added to retrieve location."""
    def __init__(self, gamefile, pointer_locations, text_location):
        self.gamefile = gamefile
        self.constant = self.gamefile.pointer_constant
        self.pointer_locations = pointer_locations
        self.text_location = text_location

    def text(self):
        pass

    def edit(self, diff):
        pass



class DumpExcel(object):
    """
    Takes a dump excel path, and lets you get a block's translations from it.
    """
    def __init__(self, path, control_codes={}):
        self.path = path
        self.workbook = load_workbook(self.path)
        self.control_codes = control_codes

    def get_translations(self, block):
        """Get the translations for a file."""
        # So they can make use of Translation() objects as well.
        trans = []    # translations[offset] = Translation()
        worksheet = self.workbook.get_sheet_by_name(block.gamefile.filename)

        for row in worksheet.rows[1:]:  # Skip the first row, it's just labels
            try:
                offset = int(row[0].value, 16)
            except TypeError:
                # Either a blank line or a total value. Ignore it.
                break
            if block.start <= offset < block.stop:
                japanese = row[1].value
                english = row[3].value

                #if isinstance(japanese, long):
                #    # Causes some encoding problems? Trying to skip them for now
                #    continue

                # Yeah this is important - blank strings are None (non-iterable), so use "" instead.
                if not english:
                    english = ""

                trans.append(Translation(block, offset, japanese, english))
        return trans

class PointerExcel(object):
    def __init__(self, path):
        self.path = path
        self.workbook = load_workbook(self.path)

    def get_pointers(self, block):
        pass
