#!/usr/bin/python3
import unittest
import os
import subprocess
import shutil
import sys

TMP_TESTING_DIR = None
TMP_TESTING_SUB_DIR = None
PASSWORD = 'testing123'
DEBUG_MODE = False
ENCRYPTED_FILE_EXT = '.gpg'

class MyTest(unittest.TestCase):

    def setUp(self):
        rm_dir_tree(TMP_TESTING_SUB_DIR)

    def tearDown(self):
        pass

    def testCleanUpFolder(self):
        ''' Test that empty folders (after a file is deleted) are deleted'''

        base_folder = TMP_TESTING_SUB_DIR + '/testCleanUpFolder/base'
        target_folder = TMP_TESTING_SUB_DIR + '/testCleanUpFolder/target'
        config_dict = {
            'base_folder': base_folder,
            'target_folder': target_folder
        }
        file1_full_base_directory = base_folder + '/aaa/bbb/ccc/ddd'
        file1_base = file1_full_base_directory + '/file1.txt'
        file1_full_target_directory = target_folder + '/aaa/bbb/ccc/ddd'
        file1_target = file1_full_target_directory + '/file1.txt' + ENCRYPTED_FILE_EXT
        file_contents = 'bla bla'
        create_or_modify_file(file1_base, file_contents)


        file2_full_base_directory = base_folder + '/aaa/bbb/alt'
        file2_base = file2_full_base_directory + '/file2.txt'
        file2_full_target_directory = target_folder + '/aaa/bbb/alt'
        file2_target = file2_full_target_directory + '/file2.txt' + ENCRYPTED_FILE_EXT
        file_contents = 'bla bla'
        create_or_modify_file(file2_base, file_contents)

        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)

        # sanity test
        self.assertTrue(os.path.exists(file1_full_target_directory), "The first file's path ({}) exists.".format(file1_full_target_directory))
        self.assertTrue(os.path.exists(file2_full_target_directory), "The seconds file's path ({}) exists.".format(file2_full_target_directory))

        os.unlink(file1_base)

        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)
        deleted_folder = target_folder + '/aaa/bbb/ccc'

        self.assertFalse(os.path.exists(deleted_folder), '{} is gone'.format(deleted_folder))
        self.assertTrue(os.path.exists(file2_target), '{} file is still there.'.format(file2_target))

    def testMovedFile(self):
        ''' Test moving a file '''
        base_folder = TMP_TESTING_SUB_DIR + '/testMovedFile/base'
        target_folder = TMP_TESTING_SUB_DIR + '/testMovedFile/target'
        config_dict = {
            'base_folder': base_folder,
            'target_folder': target_folder

        }

        file1_base = base_folder + '/xxx/file1.txt'
        file1_target = target_folder + '/xxx/file1.txt' + ENCRYPTED_FILE_EXT
        file1_contents = 'this is file 1.'
        create_or_modify_file(file1_base, file1_contents)

        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)

        new_file1_base = base_folder + '/xxx/new_file1.txt'
        new_file1_target = target_folder + '/xxx/new_file1.txt' + ENCRYPTED_FILE_EXT
        os.rename(file1_base, new_file1_base)
        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)

        self.assertTrue(os.path.exists(new_file1_target), 'The new file exists in the new location')
        self.assertFalse(os.path.exists(file1_target), 'The new file exists does not exist in the old location')

    def testAllBasic(self):
        ''' Test adding a file, removing 1, and updating 1'''
        base_folder = TMP_TESTING_SUB_DIR + '/testallbasic/base'
        target_folder = TMP_TESTING_SUB_DIR + '/testallbasic/target'
        config_dict = {
            'base_folder': base_folder,
            'target_folder': target_folder

        }

        file1_base = base_folder + '/xxx/file1.txt'
        file1_target = target_folder + '/xxx/file1.txt' + ENCRYPTED_FILE_EXT
        file1_contents = 'this is file 1.'
        create_or_modify_file(file1_base, file1_contents)

        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)

        self.assertTrue(
            is_encrypt_as(file1_target, file1_contents),
            'First file is encrypted in target directory')

        # add a new file
        file2_base = base_folder + '/yyy/file2.txt'
        file2_target = target_folder + '/yyy/file2.txt' + ENCRYPTED_FILE_EXT
        file2_contents = 'this is file 2.'
        create_or_modify_file(file2_base, file2_contents)

        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)
        self.assertTrue(
            is_encrypt_as(file1_target, file1_contents),
            'First file still is encrypted in target directory')
        self.assertTrue(
            is_encrypt_as(file2_target, file2_contents),
            '2nd file is encrypted in target directory')

        # modify file
        file1_contents = 'new file1 contents here!'
        create_or_modify_file(file1_base, file1_contents)
        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)
        self.assertTrue(
            is_encrypt_as(file1_target, file1_contents),
            'First file has changed contents')
        self.assertTrue(
            is_encrypt_as(file2_target, file2_contents),
            '2nd file is encrypted in target directory just like before')

        # remove file
        print('REMOVING:{}'.format(file2_base))
        os.unlink(file2_base)
        self.run_encrypt_backup_wo_error(config_dict, clean_target = False, clean_base = False)
        self.assertTrue(
            is_encrypt_as(file1_target, file1_contents),
            'First file is still there with expected contents.')
        self.assertFalse(os.path.exists(file2_target),
            'File 2 is removed.')

    def testFirstRun(self):
        ''' Test with nothing to do (2 runs).'''

        config_dict = {
            'base_folder': TMP_TESTING_SUB_DIR + '/testFirstRun/base/tmp',
            'target_folder': TMP_TESTING_SUB_DIR + '/testFirstRun/target/tmp'
        }
        result = run_encrypt_back_program(config_dict)
        self.assertEqual(result['ret_val'], 0, 'first empty run ok')

        result = run_encrypt_back_program(config_dict)
        self.assertEqual(result['ret_val'], 0, 'second empty run ok')

    def run_encrypt_backup_wo_error(self, config_dict, **args):
        result = run_encrypt_back_program(config_dict, **args)
        if result['ret_val'] != 0:
            raise Exception('run failed and returned:{}'.format(result['ret_val']))

def run_encrypt_back_program(config_dict, clean_base = True, clean_target = True):
    debug('in run_encrypt_back_program with clean_base={} and clean_target={}'.format(clean_base, clean_target))

    for manditory_param in ('base_folder', 'target_folder'):
        if manditory_param not in config_dict:
            raise Exception("don't call with function without config_dict['{}']".format(manditory_param))
    config_dict.setdefault('file_extension', ENCRYPTED_FILE_EXT)
    config_dict.setdefault('debug_mode', 'true')
    config_dict.setdefault('password', PASSWORD)

    if clean_base:
        rm_dir_tree(config_dict['base_folder'])
    if clean_target:
        rm_dir_tree(config_dict['target_folder'])

    config_file_name = TMP_TESTING_DIR + '/test_config_file.conf'
    config_file = open(config_file_name, 'w')
    for key, value in config_dict.items():
        config_file.write('{}={}\n'.format(key, value))
    config_file.close()
    cmd = 'python encrypt_backup.py {}'.format(config_file_name)

    return run_program(cmd)

def run_program(cmd):
    debug('\trunning:' + cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    ret_val = p.wait()
    stdout = p.stdout.read().decode('utf-8')
    stderr = p.stderr.read().decode('utf-8')
    p.stdout.close()
    p.stderr.close()

    if ret_val != 0:
        debug('\t' + cmd + ' failed')
    else:
        debug('\t' + cmd + ' worked')

    debug('\tstdout:' + stdout)
    debug('\tstderr:' + stderr)

    return {'ret_val':ret_val, 'stdout':stdout, 'stderr':stderr}

def create_or_modify_file(file_name, contents):
    dir = os.path.dirname(file_name)
    debug('dir:' + dir)
    if not(os.path.exists(dir)):
        debug('making dir:' + dir)
        os.makedirs(dir, exist_ok = True)
    debug('making file:' + file_name)
    fh = open(file_name, 'w')
    fh.write(contents)
    fh.close()

def is_encrypt_as(file_name, contents):

    # sends the result to stdout
    # echo 'sec3rt p@ssworD' | gpg --batch --passphrase-fd 0 --decrypt secert3.txt.gpg
    result = run_program("echo '{}' | gpg --batch --passphrase-fd 0 --decrypt {}".format(PASSWORD, file_name))
    return result['stdout'] == contents

def rm_dir_tree(path):
    debug('attempting to remove:' + path)
    if os.path.exists(path):
        # shutil.rmtree(path, onerror = on_rm_error )
        run_program('rm -rf {}'.format(path))


def on_rm_error( func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    debug('in on_rm_error')
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )

def debug(debug_str):
    if DEBUG_MODE == True:
        sys.stderr.write(debug_str + '\n')

if __name__ == '__main__':

    if len(sys.argv) == 1:
        TMP_TESTING_DIR = os.getcwd()
    elif len(sys.argv) == 2:
        TMP_TESTING_DIR = sys.argv[1]
    else:
        sys.stderr.write('Usage: one optional argument that is temp working directory for this program\n')
        sys.exit(1)
    TMP_TESTING_SUB_DIR = TMP_TESTING_DIR + '/testing'
    # command line args screw up the unittest module (yes, weird but true)
    del sys.argv[1:]

    unittest.main()
