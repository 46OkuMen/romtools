## Pachy98 TODO

* Write more generic test cases with mocks

* Write incredibly basic test cases
	* EVO: Done
	* Rusty: Done
	* CRW: Done
	* Die Bahnwelt
	* Brandish 2
	* Pass disks as command line argument
	* Pass disk as subdirectory
	* Target disk with SJIS filename
	* Pass read-only disk

* Better failure when trying to insert a file after deleting
	* meunierd suggested "So I think the way it works now is something like: BACKUP, ATTEMPT, FAIL, RESTORE FROM BACKUP // But what might be more durable is to BACKUP, APPLY TO BACKUP, and just clean up if we fail // and overwrite if we succeed"

* Check out NDC on Touhou games
	* The directory 5_怪綺談 gets mangled into (null) on Mac but not Windows...
		* Possibly a bug in ndc. Works in ND, NDC Win, but not NDC Mac

* Investigate silent failure on Estonian locale system
	* Last thing in log: "INFO:root:"C:\Users\fushi\Dropbox\46\46\bin\ndc" G "C:\Users\fushi\Dropbox\46\46\46 Okunen Monogatari - The Shinkaron.hdi" 0 "OPENING.EXE" "C:\Users\fushi\Dropbox\46\46"

* Those tests are rather slow. It's about 4s for a speedrun of pachy98
	* Would be faster with mocked disks

* Windows XP + Vista support? Need to try building it on an XP system
	* Pyinstaller does support XP.