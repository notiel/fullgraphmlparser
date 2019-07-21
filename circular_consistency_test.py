import os
import shutil
import stat
import subprocess
import sys
import unittest
from shutil import copyfile

import pytest

import cpp_to_graphml
import graphmltoqm


def getQmWithArgs():
    if sys.platform == 'win32':
        return [os.environ.get('PROGRAMFILES(X86)') + '/qm/bin/qm']

    if sys.platform == 'linux':
        # 1. On Linux, QM installer just unpacks itself wherever it was run,
        #    and not in any standard folder. As for now we only use Linux on Travis,
        #    let's use some well-defined path where we can install QM to.
        # 2. We use qm.sh instead of qm as recommended by https://www.state-machine.com/qm/gs_run.html#gs_run_linux
        # 3. We add xvfb-run so it can run in screen-less environments (e.g. Travis)
        return ['xvfb-run', os.path.expanduser('~/qm/bin/qm.sh')]

    raise NotImplementedError('Only windows and linux are supported')

# Does full conversion cycle (C++ --> graphml --> qm --> C++)
class CircularConsistencyTest(unittest.TestCase):
    def removeOutputFolder(self):
        if (os.path.exists('testdata/test_output')):
            # Special magic is required to delete read-only files on Windows.
            # See https://bugs.python.org/issue19643 and https://hg.python.org/cpython/rev/31d63ea5dffa
            def remove_readonly(action, name, exc):
                os.chmod(name, stat.S_IWRITE)
                os.remove(name)
            shutil.rmtree('testdata/test_output',  onerror=remove_readonly)

    def setUp(self):
        self.removeOutputFolder()
        os.makedirs('./testdata/test_output')

    def tearDown(self):
       self.removeOutputFolder()

    def testFullCycle(self):
        parser = cpp_to_graphml.StateMachineParser(cpp_file_path='./testdata/oregonPlayer.cpp')
        sm1 = parser.Parse()
        cpp_to_graphml.StateMachineWriter(sm1).WriteToFile('./testdata/test_output/oregonPlayer.graphml', './testdata/oregonPlayer.graphml')
        graphmltoqm.main('./testdata/test_output/oregonPlayer.graphml')
        shutil.copy('./testdata/qhsm.h', './testdata/test_output')
        shutil.copy('./testdata/eventHandlers.h', './testdata/test_output')
        subprocess.run(getQmWithArgs() + ['./testdata/test_output/oregonPlayer.qm', '-c'], check=True, timeout=10)
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

        # This one is quite fragile as literally any change in the output will break it. Not sure if it's actually needed.
        with open('./testdata/oregonPlayer.cpp', 'r') as f:
            sm1_cpp_content = f.read()
        with open('./testdata/test_output/oregonPlayer.cpp', 'r') as f:
            sm2_cpp_content = f.read()
        self.assertEqual(sm1_cpp_content, sm2_cpp_content)

if __name__ == '__main__':
    unittest.main()
