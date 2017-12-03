### TODO
* Write incredibly basic test cases
	* EVO: Done
	* Rusty
	* CRW
	* Die Bahnwelt
	* Brandish 2
	* Pass disks as command line argument
	* Pass disk as subdirectory
	* Target disk with SJIS filename
	* Pass read-only disk

* Brandish 2 fixes
	* Error patching the FDI version when trying to insert some file
	* Doesn't detect the HDI version immediately, but it can patch it

* Better failure when trying to insert a file after deleting
	* meunierd suggested "So I think the way it works now is something like: BACKUP, ATTEMPT, FAIL, RESTORE FROM BACKUP // But what might be more durable is to BACKUP, APPLY TO BACKUP, and just clean up if we fail // and overwrite if we succeed"

* Check out NDC on Touhou games

* Investigate DLL detection error

* Investigate Estonian locale error

* Those tests are rather slow.