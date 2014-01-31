#!/usr/bin/python3

''' This program copies over a directory recursively to another folder and 
encrypts the contents (in the target folder). Most of the meat of this program
is copying and encrypting changed content and removing folders which become
empty. The program requires git and gpg to call from the command line.
I created this program to be run by cron and to encrypt important files and
move then into a folder to be picked up dropbox.

Note one mandatory argument is passed to the program. This is the file name
of the configuration file.
'''

import os
import subprocess
import re
import sys

CONFIG_FILE = 'encrypt_backup.conf'
VALID_CONFIG_VARIABLES = {'base_folder', 'target_folder', 'file_extension', 'password', 'debug_mode'}
MANDITORY_CONFIG_VARIABLE = {'base_folder', 'target_folder', 'password'}
debug_mode = False

def first_run_todo(base_folder, target_folder):
    ''' Do some things that need to be once when the program is run for 
    the first time or when certain config file setttings change.'''

    for dir in (base_folder, target_folder):
        os.makedirs(dir, exist_ok = True)

    # If there is no git repo create one 
    os.chdir(base_folder)
    if not(os.path.exists('.git')):
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
    os.chdir(config_values['target_folder'])
    delete_files(files['to_delete'])
    add_encrypted_files(files['to_add'], config_values)

    # do a git commit only now that all the changes are encrypted
    os.chdir(config_values['base_folder'])
    for file in (files['to_add'] + files['to_delete']):
        run('git add {}'.format(file))
    # FIXME
    #run("git commit -a -m 'commit from encrypt backup program'")


def process_config_file(config_file_name):
    ''' Parse the main configuration file and process it'''

    global debug_mode

    config_values = {}
    with open(config_file_name, 'r') as fh:
        for line in fh:
            if not(line.startswith('#')):
                if re.match(r'\s*$', line):
                    continue
                line = line.strip()
                (orig_config_name, config_value) = line.split('=')
                config_name = orig_config_name.lower().strip()
                config_value = config_value.lower().strip()
                if config_name not in VALID_CONFIG_VARIABLES:
                    raise Exception('In configuration file:{} config variable: {} is not recognized'.format(config_file_name, orig_config_name))
                config_values[config_name] = config_value

    for mand_config_key in MANDITORY_CONFIG_VARIABLE:
        if mand_config_key not in config_values:
            raise Exception('In configuration file:{} missing varible:{}'.format(config_file_name, mand_config_key))

    # set some defaults
    if 'file_extension' not in config_values:
        config_values['file_extension'] = ''
    if ('debug_mode' in config_values) and \
        (config_values['debug_mode'].lower() in ('t', 'true', '1')):
        debug_mode = True
    
    return config_values

def add_encrypted_files(files_to_add, config_values):
    ''' Encrypted and copy over the files to the target dir '''

    # Example of working gpg command
    # echo 'sec3rt p@ssworD' | gpg --batch --passphrase-fd 0 --output secert3.txt.gpg --symmetric secert.txt

    command_to_encrypt = "echo '{0}' | gpg --batch --passphrase-fd 0 --output {{temp_out_file}} --symmetric {{in_file}} > {{out_file}}".format(config_values['password'])
    
    for file in files_to_add:

        # make the parent folder if it isn't there
        out_file = config_values['target_folder'] + os.path.sep + file + config_values['file_extension']
        out_folder = os.path.dirname(out_file)
        os.makedirs(out_folder)

        temp_out_file = config_values['base_folder'] + os.path.sep + file + config_values['file_extension']

        in_file =  config_values['base_folder'] + os.path.sep + file

        run(command_to_encrypt.format(temp_out_file = temp_out_file, in_file = in_file, out_file = out_file))


def delete_files(files_to_delete):
    ''' Delete all the files and folders from the target dir that are no 
    longer around. Note the 99% of the work is deleting folders that just 
    became empty.'''

    potential_folders_to_delete = {}
    for file in files_to_delete:
        # FIXME 
        #os.remove(file)
        debug('removing file:{}'.format(file))

        path_parts = file.split(os.path.sep)[:-1]
        last_dir = potential_folders_to_delete
        for dir in path_parts:
            if dir not in last_dir:
                last_dir[dir] = {}
            last_dir = last_dir[dir] 
    delete_folders(potential_folders_to_delete, '')

def delete_folders(folders_dict, base_folder):
    for dir in folders_dict:
        delete_folders(folders_dict[dir])
        try:
            folder_to_delete = base_folder + os.path.sep + dir 
            # FIXME
            #os.remove(folder_to_delete)
            debug('removing folder:{}'.format(folder_to_delete))
        except OSError:
            pass

def get_files_to_process():
    ''' Get all files that have new, deleted, or changed '''

    # git status --porcelain
    # ex output:
    # M tmp2/file.txt
    # D to_removed.txt
    # ?? bla.txt
    return_val = {'to_add': [], 'to_delete':[]}
    output = run('git status --porcelain')['stdout']
    add_or_modified_regex = re.compile(r'(?:M|\?\?)\s+(.+)$')
    deleted_regex = re.compile(r'(?:D)\s+(.+)$')
    for line in output:
        line = line.strip()
        match_obj = add_or_modified_regex.match(line)
        if match_obj:
            return_val['to_add'].append(match.group(1))
            continue
        match_obj = deleted_regex.match(line)
        if match_obj:
            return_val['to_delete'].append(match.group(1))
    debug
    return return_val
        
                
def run(cmd):
    ''' Run a command line program, gather it's output, and throw a exception
    if the program failed.'''

    debug('running shell command:{}'.format(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    ret_val = p.wait()
    stdout = p.stdout.read().decode('utf-8')
    stderr = p.stderr.read().decode('utf-8')
    p.stdout.close()
    p.stderr.close()
    if (ret_val != 0):
        sys.stderr.write('Error with command:%s\nstdout:%s\nstderr:%s\n' % (cmd, stdout, stderr))
        sys.exit(ret_val)
    return {'stdout':stdout, 'stderr':stderr}

def debug(input_str):
    global debug_mode
    if debug_mode:
        print(input_str)

if __name__ == '__main__':
    main()
