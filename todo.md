## Pachy98 TODO
* Build 0.19.0 for B2R2 team

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

* Brandish 2 fixes
	* Error patching the FDI version when trying to insert some file
		* That file is bigger than the destination disk. Not something I can address.
	* Doesn't detect the HDI version immediately, but it can patch it
		* Fixed in local copy.

* Better failure when trying to insert a file after deleting
	* meunierd suggested "So I think the way it works now is something like: BACKUP, ATTEMPT, FAIL, RESTORE FROM BACKUP // But what might be more durable is to BACKUP, APPLY TO BACKUP, and just clean up if we fail // and overwrite if we succeed"

* Check out NDC on Touhou games
	* The directory 5_怪綺談 gets mangled into (null) on Mac but not Windows...
		* Possibly a bug in ndc. Works in ND, NDC Win, but not NDC Mac

* Investigate DLL error on a Portuguese locale system
	* "pachy98.exe - Ponto de entrada nao encontrado" / "Nao foi possivel localizar o ponto de entrada do procedimento urctbase.terminate na biblioteca de vinculo dinamico api-ms-win-crt-runtime-l1-1-0.dll."

* Investigate silent failure on Estonian locale system
	* Last thing in log: "INFO:root:"C:\Users\fushi\Dropbox\46\46\bin\ndc" G "C:\Users\fushi\Dropbox\46\46\46 Okunen Monogatari - The Shinkaron.hdi" 0 "OPENING.EXE" "C:\Users\fushi\Dropbox\46\46"

* Those tests are rather slow. It's about 4s for a speedrun of pachy98
	* Would be faster with mocked disks
