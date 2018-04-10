                           -------------------------------
                                 46 OkuMen Present
                                      Pachy98
                                      v0.20.1
                           -------------------------------

------------------------
Table of Contents
------------------------
1.0 Basic Information
	1.1 Version History
	1.2 Usage
		1.2.1 Patching a Game
		1.2.2 Writing a Config
2.0 Credits
3.0 License
4.0 Contact
------------------------

------------------------
1.0 Basic Information
------------------------

1.1 Version History
------------------------
v0.20.1 - Apr 10, 2018 - Fixed order of fields in generated configs.
v0.20.0 - Apr 07, 2018 - Added config generation. schema.json no longer required.
v0.19.1 - Dec 09, 2017 - Bugfixes and support on wider variety of systems.
v0.17.3 - Jul 10, 2017 - Add support for XDF and DUP images. Bugfixes.
v0.15.0 - Jul 01, 2017 - Initial public release, included with CRW - Metal Jacket.

1.2 Usage
------------------------

1.2.1 Patching a Game
------------------
	Place the game disk images in the same directory as Pachy98. Run Pachy98 and follow the directions.
	Your original disk images will be stored in a folder called "backup".

1.2.2 Writing a Config
------------------
	If you want to use Pachy98 to apply a patch, you need to create a config file to tell it what files to look for and patch in a disk image.

	Since v0.20.0, Pachy98 can generate this config file from scratch if you tell it which disks you're working with. From the command line, enter this command:
		./pachy98.exe -generate Disk1.fdi Disk2.fdi Disk1Patched.fdi Disk2Patched.fdi

	Pachy98 will compare all the files in Disk1.fdi and Disk1Patched.fdi, generate xdelta patches for the ones that differ, and generate a config file called Pachy98-Disk1.json. You can further modify this file, to specify things like your game name and group name.

	If you want to do anything more complex, like try multiple patches on a file, or consider a file optional, you should see the more detailed documentation:
		https://46okumen.com/pachy98/

------------------------
2.0 Credits
------------------------
hollowaytape - Development
meunierd - Development
kuoushi - QA, Design
euee - Special Thanks

------------------------
3.0 License
------------------------
Pachy98 uses the Apache License 2.0. See LICENSE for more information.

------------------------
4.0 Contact
------------------------
If you run into any issues, send an email to hollowaytape AT retro-type DOT com.
