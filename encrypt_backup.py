#!/usr/bin/python3

''' This program copies over a directory recursively to another folder and
encrypts the contents (in the target folder). Most of the meat of this program
is copying and encrypting changed content and removing folders that become
empty.  I created this program to be run by cron and to encrypt important files
and move then into a folder to be picked up dropbox. The use case of this program is if you login into dropbox (or a simliar service) frequently from less safe computers but you still want to backup very secure documents.

Note one mandatory argument is passed to the program. This is the file name
of the configuration file.

Requirement.
- Only works on unix 
- git (tested with version 1.7.9.5)
- gpg (tested with version 1.4.11). No key pair need (runs with symetric encryption)
- Won't work on python2.X. Was tested on python3.2 and need no extra python
libraries.
'''

import os
import subprocess
import re
import sys

CONFIG_FILE = 'encrypt_backup.conf'
VALID_CONFIG_VARIABLES = {'base_folder', 'target_folder', 'file_extension',
    'password', 'debug_mode'}
MANDITORY_CONFIG_VARIABLE = {'base_folder', 'target_folder', 'password'}
DEBUG_MODE = False

def first_run_todo(base_folder, target_folder):
    ''' Do some things that need to be once when the program is run for
    the first time or when certain config file setttings change.'''

    for dir_to_create in (base_folder, target_folder):
        os.makedirs(dir_to_create, exist_ok=True)

    # If there is no git repo create one
    os.chdir(base_folder)
    if not os.path.exists('.git'):
        run('git init')

def main():

    if len(sys.argv) != 2:
        sys.stderr.write('Usage:encrypt_backup.py <config_file>\n')
        sys.exit(1)

    config_file_name = sys.argv[1]
    config_values = process_config_file(config_file_name)
    debug('config_values' + str(config_values))

    first_run_todo(config_values['base_folder'], config_values['target_folder'])

    # normalize path names (ie remove a extra '/' at end if present)
    for i in ('base_folder', 'target_folder'):
        config_values[i] = os.path.normpath(config_values[i])

    # delete or encrypt (new or changed) files in the target dir
    files = get_files_to_process()

    if (len(files['to_add']) == 0) and len(files['to_delete']) == 0:
        debug('nothing new to encrypt and copy. exiting...')
        sys.exit(0)
    debug('files to process:{}'.format(files))
    delete_files(config_values['target_folder'], files['to_delete'],
        config_values['file_extension'])
    add_encrypted_files(config_values['target_folder'], files['to_add'],
        config_values)

    # do a git commit only now that all the changes are encrypted
    os.chdir(config_values['base_folder'])
    for file in files['to_add'] + files['to_delete']:
        run("git add '{}'".format(file))
    run("git commit -a -m 'commit from encrypt backup program'")


def process_config_file(config_file_name):
    ''' Parse the main configuration file and process it'''

    global DEBUG_MODE

    config_values = {}
    with open(config_file_name, 'r') as fh:
        for line in fh:
            if line.startswith('#') or re.match(r'\s*$', line):
                continue
            line = line.strip()
            (orig_config_name, config_value) = line.split('=')
            config_name = orig_config_name.lower().strip()
            config_value = config_value.strip()
            if config_name not in VALID_CONFIG_VARIABLES:
                raise Exception('In configuration file:{} config variable: {}\
                    is not recognized'.format(config_file_name,
                    orig_config_name))
            config_values[config_name] = config_value


    for mand_config_key in MANDITORY_CONFIG_VARIABLE:
        if mand_config_key not in config_values:
            raise Exception('In configuration file:{} missing \
                varible:{}'.format(config_file_name, mand_config_key))

    # set some defaults
    if 'file_extension' not in config_values:
        config_values['file_extension'] = ''
    if ('debug_mode' in config_values) and \
        (config_values['debug_mode'].lower() in ('t', 'true', '1')):
        DEBUG_MODE = True

    return config_values

def add_encrypted_files(target_folder, files_to_add, config_values):
    ''' Encrypted and copy over the files to the target dir '''

    os.chdir(target_folder)

    # Example of working gpg command
    # echo 'sec3rt p@ssworD' | gpg --batch --passphrase-fd 0 --output \
    #   secert3.txt.gpg --symmetric secert.txt
    command_to_encrypt = "echo '{0}' | gpg --batch --passphrase-fd 0 --output \
        '{{out_file}}' --symmetric '{{in_file}}'".format(config_values['password'])

    for file in files_to_add:

        # make the parent folder if it isn't there
        out_file = '{}/{}{}'.format(config_values['target_folder'], file,
            config_values['file_extension'])
        out_folder = os.path.dirname(out_file)
        os.makedirs(out_folder, exist_ok=True)

        # gpg won't overwrite a file. in an older version of the file
        # exists remove it first
        if os.path.exists(out_file):
            os.unlink(out_file)

        in_file = '{}/{}'.format(config_values['base_folder'], file)

        run(command_to_encrypt.format(in_file=in_file, out_file=out_file))


def delete_files(target_folder, files_to_delete, file_extension):
    ''' Delete all the files and folders from the target dir that are no
    longer around. Note the 99% of the work is deleting folders that just
    became empty.'''

    os.chdir(target_folder)
    all_folders_to_delete = []
    for file in files_to_delete:
        file += file_extension
        os.remove(file)

        all_folders_to_delete.append(file.split(os.path.sep)[:-1])
    debug('all_folders_to_delete:{}'.format(all_folders_to_delete))
    delete_folders(target_folder, all_folders_to_delete)

def delete_folders(target_folder, all_folders_to_delete):
    ''' Prune as much of the empty directories as I can'''

    for long_path in all_folders_to_delete:
        folder_len = len(long_path)
        for i in range(folder_len):

            folder_to_delete = '{}/{}'.format(target_folder,
                '/'.join(long_path[:folder_len - i]))
            try:
                os.rmdir(folder_to_delete)
            except OSError:
                break

def get_files_to_process():
    ''' Get all files that have new, deleted, or changed '''

    # git status --porcelain -uall
    # ex output:
    # M tmp2/file.txt
    # D to_removed.txt
    # ?? bla.txt
    return_val = {'to_add': [], 'to_delete':[]}
    output = run('git status --porcelain -uall')['stdout']
    debug('git output:{}'.format(output))
    add_or_modified_regex = re.compile(r'(?:M|\?\?)\s+(.+)$')
    deleted_regex = re.compile(r'(?:D)\s+(.+)$')
    for line in output.split('\n'):
        line = line.strip()
        debug('line:{}'.format(line))
        match_obj = add_or_modified_regex.match(line)
        if match_obj:
            if os.path.isdir(match_obj.group(1)):
                continue
            return_val['to_add'].append(match_obj.group(1))
            continue
        match_obj = deleted_regex.match(line)
        if match_obj:
            if not os.path.isdir(match_obj.group(1)):
                return_val['to_delete'].append(match_obj.group(1))
    debug('files_to_process:{}'.format(return_val))
    return return_val

def run(cmd):
    ''' Run a command line program, gather it's output, and throw a exception
    if the program failed.'''

    debug('running shell command:{}'.format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True)
    ret_val = p.wait()
    stdout = p.stdout.read().decode('utf-8')
    stderr = p.stderr.read().decode('utf-8')
    p.stdout.close()
    p.stderr.close()
    if ret_val != 0:
        sys.stderr.write('Error with command:%s\nstdout:%s\n\
            stderr:%s\n'.format(cmd, stdout, stderr))
        sys.exit(ret_val)
    return {'stdout':stdout, 'stderr':stderr}

def debug(input_str):
    if DEBUG_MODE:
        sys.stderr.write(input_str + '\n')

if __name__ == '__main__':
    main()
