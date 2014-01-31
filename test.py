import unittest
import os
import subprocess
import shutil
import sys

cwd = os.getcwd()
 
class MyTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testStart(self):
        self.assertEqual(1,1, 'testing 1 2 3')
    
    def testFirstRun(self):
        ''' Test with nothing to do (2 runs).'''

        config_dict = {
            'base_folder': cwd + 'test/testFirstRun/base/tmp',
            'target_folder': cwd + 'test/testFirstRun/target/tmp'
        }
        result = run_program(config_dict)
        self.assertEqual(result['ret_val'], 0, 'first empty run ok')

        result = run_program(config_dict)
        self.assertEqual(result['ret_val'], 0, 'second empty run ok')
        
def run_program(config_dict, clean_base = True, clean_target = True, print_failed_run = True):
    for manditory_param in ('base_folder', 'target_folder'):
        if manditory_param not in config_dict:
            raise Exception("don't call with function without config_dict['{}']".format(manditory_param))
    config_dict.setdefault('file_extension', '.gpg')
    config_dict.setdefault('debug_mode', 'true')
    config_dict.setdefault('password', 'P@ssW@rd!!!')

    if clean_base and os.path.exists(config_dict['base_folder']):
        shutil.rmtree(config_dict['base_folder'])
    if clean_target and os.path.exists(config_dict['target_folder']):
        shutil.rmtree(config_dict['target_folder'])
   
    config_file_name = cwd + '/test_config_file.conf'
    config_file = open(config_file_name, 'w')
    for key, value in config_dict.items():
        config_file.write('{}={}\n'.format(key, value))
    config_file.close()
    cmd = 'python3 encrypt_backup.py {}'.format(config_file_name)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    ret_val = p.wait()
    stdout = p.stdout.read().decode('utf-8')
    stderr = p.stderr.read().decode('utf-8')
    p.stdout.close()
    p.stderr.close()

    if print_failed_run and (ret_val != 0):
        debug(cmd + ' failed')
        debug('stdout:' + stdout)
        debug('stderr:' + stderr)

    return {'ret_val':ret_val, 'stdout':stdout, 'stderr':stderr}

def debug(debug_str):
    sys.stderr.write(debug_str + '\n')

if __name__ == '__main__':
    unittest.main()
