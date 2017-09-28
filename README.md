# romtools
Tools for tasks common to several of 46 OkuMen's romhacking projects.

* pachy98.py - A flexible patcher for JP PC game disk images. Distributed as Pachy98.exe.
* disk.py - Wrapper for NDC for reading disk images, and extracting/inserting files.
* patch.py - Wrapper for xdelta3 for generating and applying patches.
* dump.py - Classes for dumps of text and pointers.
* lzss.py - Utilities for Rusty LZSS compression and decompression. Not yet adapted for other uses.
* rominfo.py - Skeleton/boilerplate for new romhacking projects.

## Requirements
* Python 3.5
* Python module "Bitstring"
* Pyinstaller
* NDC.exe
* xdelta3.exe

## Building Pachy98
```pyinstaller pachy98.spec```