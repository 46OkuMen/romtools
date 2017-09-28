import os
import xlsxwriter

dir = os.curdir


def dump(files):
    worksheet = workbook.add_worksheet('Everything')
    worksheet.write(0, 0, 'Offset', header)
    worksheet.write(0, 1, 'Japanese', header)
    worksheet.write(0, 2, 'File', header)
    worksheet.write(0, 3, 'Comments', header)

    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:B', 60)
    worksheet.set_column('C:C', 15)
    worksheet.set_column('D:D', 60)
    row = 1
    for filename in files:
        with open(os.path.join(rom_contents_dir, filename), 'rb') as f:
            contents = f.read()

            cursor = 0
            sjis_buffer = b""
            sjis_buffer_start = 0
            sjis_strings = []
            while cursor < len(contents):

                # First byte of SJIS text. Read the next one, too
                if 0x80 <= contents[cursor] <= 0x9f or 0xe0 <= contents[cursor] <= 0xef:
                    #print(bytes(contents[cursor]))
                    sjis_buffer += contents[cursor].to_bytes(1, byteorder='little')
                    cursor += 1
                    sjis_buffer += contents[cursor].to_bytes(1, byteorder='little')

                # ASCII space
                elif contents[cursor] == 0x20:
                    sjis_buffer += b" "

                # C string formatting with %
                #elif contents[cursor] == 0x25:
                #    #sjis_buffer += b'%'
                #    cursor += 1
                #    if contents[cursor]

                # End of continuous SJIS string, so add the buffer to the strings and reset buffer
                else:
                    if len(sjis_buffer) > 2:
                        sjis_strings.append((sjis_buffer_start, sjis_buffer))
                    sjis_buffer = b""
                    sjis_buffer_start = cursor+1
                cursor += 1
                #print(sjis_buffer)

            # Catch anything left after exiting the loop
            if sjis_buffer:
                sjis_strings.append((sjis_buffer_start, sjis_buffer))


            if len(sjis_strings) == 0:
                continue

            for s in sjis_strings:
                loc = '0x' + hex(s[0]).lstrip('0x').zfill(5)
                try:
                    jp = s[1].decode('shift-jis')
                except UnicodeDecodeError:
                    print("Couldn't decode that")
                    continue 

                if len(jp.strip()) == 0:
                    continue
                print(loc, jp)

                worksheet.write(row, 0, loc)
                worksheet.write(row, 1, jp)
                worksheet.write(row, 2, filename)
                row += 1

    workbook.close()

if __name__ == '__main__':
    rom_contents_dir = 'Dante98'
    workbook = xlsxwriter.Workbook('dump.xlsx')
    header = workbook.add_format({'bold': True, 'align': 'center', 'bottom': True, 'bg_color': 'gray'})
    FILES = [f for f in os.listdir(rom_contents_dir) if os.path.isfile(os.path.join(rom_contents_dir, f))]
    print(FILES)
    dump(FILES)


# TODO: DOn't really need to dump anything before a compiler message, if those are around.