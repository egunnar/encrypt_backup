encrypt_backup
==============

Encrypt changed files for dropbox

This program copies over a directory recursively to another folder and
encrypts the contents (in the target folder). Most of the meat of this program
is copying and encrypting changed content and removing folders that become
empty.  I created this program to be run by cron and to encrypt important files
and move then into a folder to be picked up dropbox. The use case of this program is if you login into dropbox (or a simliar ) frequently from less safe computers but you still want to backup very secure documents.

Note one mandatory argument is passed to the program. This is the file name
of the configuration file.

Requirement.
- Only works on unix 
- git (tested with version 1.7.9.5)
- gpg (tested with version 1.4.11). No key pair need (runs with symetric encryption)
- Won't work on python2.X. Was tested on python3.2 and need no extra python
libraries.
