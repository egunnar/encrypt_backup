import unittest
import os
import subprocess
import shutil

cwd = os.getcwd()
 
class MyTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testStart(self):
        self.assertEqual(1,1, 'testing 1 2 3')
    
    def testFirstRun(self):
        ''' Test first time program run with nothing to do.'''

        config_dict = {
            'base_folder': cwd + 'test/testFirstRun/base/tmp',
            'target_folder': cwd + 'test/testFirstRun/target/tmp'
        }
        result = run_program(config_dict)

        
def run_program(config_dict, clean_base = True, clean_target = True):
    for manditory_param in ('base_folder', 'target_folder'):
        if manditory_param not in config_dict:
            raise Exception("don't call with function without config_dict['{}']".format(manditory_param))
    config_dict.setdefault('file_extension', '.gpg')
    config_dict.setdefault('debug_mode', 'true')

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
    print('running:' + cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    ret_val = p.wait()
    stdout = p.stdout.read().decode('utf-8')
    stderr = p.stderr.read().decode('utf-8')
    p.stdout.close()
    p.stderr.close()

    return {'ret_val':ret_val, 'stdout':stdout, 'stderr':stderr}


if __name__ == '__main__':
    unittest.main()
