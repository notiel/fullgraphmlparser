import os
import shutil
import stat
import subprocess
import sys
import unittest

import cpp_to_graphml
import graphmltoqm


def getQmWithArgs():
    if sys.platform == 'win32':
        potential_qm_path = [os.environ.get('SYSTEMDRIVE') + '/qp', os.environ.get('PROGRAMFILES(X86)')]
        for p in potential_qm_path:
            potential_qm_exe = p + '/qm/bin/qm.exe'
            print('Trying to find qm.exe here: ' + potential_qm_exe)
            if os.path.isfile(potential_qm_exe):
                print('qm.exe found at %s, using it' % potential_qm_exe)
                return [potential_qm_exe]
        raise NotImplementedError('QM not found in supported locations!')

    if sys.platform == 'linux':
        # 1. On Linux, QM installer just unpacks itself wherever it was run,
        #    and not in any standard folder. As for now we only use Linux on Github Actions,
        #    let's use some well-defined path where we can install QM to.
        # 2. We use qm.sh instead of qm as recommended by https://www.state-machine.com/qm/gs_run.html#gs_run_linux
        # 3. We add xvfb-run so it can run in screen-less environments (e.g. Github Actions)
        return ['xvfb-run', './qm/bin/qm.sh']

    raise NotImplementedError('Only windows and linux are supported')


def is_boring_line(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    if line.startswith('/*'):
        return True
    return False

def remove_boring_lines(code: str) -> str:
    return '\n'.join([line for line in code.split('\n') if not is_boring_line(line)])

# Does full conversion cycle (C++ --> graphml --> qm --> C++)
class CircularConsistencyTest(unittest.TestCase):
    def removeOutputFolder(self):
        if (os.path.exists('testdata/test_output')):
            # Special magic is required to delete read-only files on Windows.
            # See https://bugs.python.org/issue19643 and https://hg.python.org/cpython/rev/31d63ea5dffa
            def remove_readonly(action, name, exc):
                os.chmod(name, stat.S_IWRITE)
                os.remove(name)

            shutil.rmtree('testdata/test_output', onerror=remove_readonly)

    def setUp(self):
        self.removeOutputFolder()
        os.makedirs('./testdata/test_output')

    def tearDown(self):
        self.removeOutputFolder()

    def testFullCycle(self):
        parser = cpp_to_graphml.StateMachineParser(cpp_file_path='./testdata/oregonPlayer.cpp')
        sm1 = parser.Parse()
        cpp_to_graphml.StateMachineWriter(sm1).WriteToFile('./testdata/test_output/oregonPlayer.graphml',
                                                           './testdata/oregonPlayer.graphml')
        graphmltoqm.main('./testdata/test_output/oregonPlayer.graphml')
        shutil.copy('./testdata/qhsm.h', './testdata/test_output')
        shutil.copy('./testdata/eventHandlers.h', './testdata/test_output')
        subprocess.run(getQmWithArgs() + ['./testdata/test_output/oregonPlayer.qm', '-c'], check=True, timeout=10,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
        parser2 = cpp_to_graphml.StateMachineParser(cpp_file_path='./testdata/test_output/oregonPlayer.cpp')
        sm2 = parser2.Parse()

        self.assertEqual(len(sm1.states), len(sm2.states))
        self.assertEqual(sm1.state_fields, sm2.state_fields)
        self.assertEqual(sm1.event_fields, sm2.event_fields)
        self.assertEqual(sm1.constructor_fields, sm2.constructor_fields)
        self.assertEqual(sm1.constructor_code, sm2.constructor_code)
        self.assertEqual(sm1.raw_h_code, sm2.raw_h_code)
        self.assertEqual(sm1.initial_state, sm2.initial_state)
        self.assertEqual(sm1.initial_code, sm2.initial_code)
        for state_name in sorted(sm1.states.keys()):
            s1 = sm1.states[state_name]
            self.assertIn(state_name, sm2.states)
            s2 = sm2.states[state_name]
            self.assertEqual(s1.state_name, s2.state_name)
            self.assertEqual(s1.parent_state_name, s2.parent_state_name, s1.state_name)

            def names(state_list):
                return [s.state_name for s in state_list]

            self.assertEqual(names(s1.child_states), names(s2.child_states))
            self.assertCountEqual(s1.event_handlers, s2.event_handlers)

        self.maxDiff = None

        # This one is quite fragile as literally any change in the output will break it. Not sure if it's actually needed.
        with open('./testdata/oregonPlayer.cpp', 'r') as f:
            sm1_cpp_content = f.read()
        with open('./testdata/test_output/oregonPlayer.cpp', 'r') as f:
            sm2_cpp_content = f.read()
        self.assertEqual(sm1_cpp_content, sm2_cpp_content)

    def checkConsistency(self, test_case_name: str):
        shutil.copy('./testdata/%s.graphml' % test_case_name, './testdata/test_output/%s.graphml' % test_case_name)
        graphmltoqm.main('./testdata/test_output/%s.graphml' % test_case_name)
        shutil.copy('./testdata/qhsm.h', './testdata/test_output')
        shutil.copy('./testdata/eventHandlers.h', './testdata/test_output')
        subprocess.run(getQmWithArgs() + ['./testdata/test_output/%s.qm' % test_case_name, '-c'], check=True,
                       timeout=10, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
        self.maxDiff = None

        # Compare Samek's vs home-brewn implementation of the generator
        with open('./testdata/test_output/%s.cpp' % test_case_name, 'r') as f:
            sm1_cpp_content = remove_boring_lines(f.read())
        with open('./testdata/test_output/%s_new.cpp' % test_case_name, 'r') as f:
            sm2_cpp_content = remove_boring_lines(f.read())
        self.assertEqual(sm1_cpp_content, sm2_cpp_content)

        with open('./testdata/test_output/%s.h' % test_case_name, 'r') as f:
            sm1_h_content = remove_boring_lines(f.read())
        with open('./testdata/test_output/%s_new.h' % test_case_name, 'r') as f:
            sm2_h_content = remove_boring_lines(f.read())
        self.assertEqual(sm1_h_content, sm2_h_content)

    def testSamekConsistencyOregon(self):
        self.checkConsistency('oregonPlayer')

    @unittest.skip("Whitespace differences")
    def testSamekConsistencyAbility(self):
        self.checkConsistency('ability')

    @unittest.skip("QM fails to process it")
    def testSamekConsistencyCharacter(self):
        self.checkConsistency('character')

    @unittest.skip("Whitespace differences")
    def testSamekConsistencyHealth(self):
        self.checkConsistency('health')

    @unittest.skip("Whitespace difference in condition, void constructor")
    def testSamekConsistencyKaCounter(self):
        self.checkConsistency('kaCounter')

    @unittest.skip("void constructor")
    def testSamekConsistencyKaTet(self):
        self.checkConsistency('kaTet')

    @unittest.skip("Whitespace differences")
    def testSamekConsistencyPlayerType(self):
        self.checkConsistency('player_type')

    @unittest.skip("void constructor")
    def testSamekConsistencyChoice1(self):
        self.checkConsistency('choice1')

if __name__ == '__main__':
    unittest.main()
