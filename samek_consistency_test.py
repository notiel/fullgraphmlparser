import os
import shutil
import subprocess
import unittest

import graphmltoqm
import test_utils


class SamekConsistencyTest(unittest.TestCase):

    def setUp(self):
        test_utils.removeOutputFolder()
        os.makedirs('./testdata/test_output')

    def tearDown(self):
        test_utils.removeOutputFolder()

    def checkConsistency(self, test_case_name: str):
        shutil.copy('./testdata/%s.graphml' % test_case_name, './testdata/test_output/%s.graphml' % test_case_name)
        graphmltoqm.main('./testdata/test_output/%s.graphml' % test_case_name)
        shutil.copy('./testdata/qhsm.h', './testdata/test_output')
        shutil.copy('./testdata/eventHandlers.h', './testdata/test_output')
        subprocess.run(test_utils.getQmWithArgs() + ['./testdata/test_output/%s.qm' % test_case_name, '-c'], check=True,
                       timeout=10, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
        self.maxDiff = None

        # Compare Samek's vs home-brewn implementation of the generator
        with open('./testdata/test_output/%s.cpp' % test_case_name, 'r') as f:
            sm1_cpp_content = test_utils.remove_boring_lines(f.read())
        with open('./testdata/test_output/%s_new.cpp' % test_case_name, 'r') as f:
            sm2_cpp_content = test_utils.remove_boring_lines(f.read())
        self.assertEqual(sm1_cpp_content, sm2_cpp_content)

        with open('./testdata/test_output/%s.h' % test_case_name, 'r') as f:
            sm1_h_content = test_utils.remove_boring_lines(f.read())
        with open('./testdata/test_output/%s_new.h' % test_case_name, 'r') as f:
            sm2_h_content = test_utils.remove_boring_lines(f.read())
        self.assertEqual(sm1_h_content, sm2_h_content)

    def testSamekConsistencyOregon(self):
        self.checkConsistency('oregonPlayer')

    @unittest.skip("Here new C++ generator generates correct, but going through Samek "
                   "leads to guard for internal trigger being completely missing. "
                   "It happens because create_qm.get_internal_trigger_code doesn't"
                   "use trigger guard in any way."
                   "There is also unrelated minor difference in the constructor:"
                   "Samek's generator puts all argument to a single line,"
                   "ours uses separate line for each argument.")
    def testAbility(self):
        self.checkConsistency('ability')

    @unittest.skip("QM fails to process it: "
                   "There is a weird INFLUENCE_AT_DOGAN choice coming from "
                   "character::alive::neutral state. It has two branches with "
                   "conditions (and no [else] branch).")
    def testCharacter(self):
        self.checkConsistency('character')

    @unittest.skip("Here new C++ generator generates correct, but going through Samek "
                   "leads to guard for internal trigger being completely missing. "
                   "It happens because create_qm.get_internal_trigger_code doesn't"
                   "use trigger guard in any way.")
    def testHealth(self):
        self.checkConsistency('health')

    def testKaCounter(self):
        self.checkConsistency('kaCounter')

    def testKaTet(self):
        self.checkConsistency('kaTet')

    def testPlayerType(self):
        self.checkConsistency('player_type')

    def testChoice1(self):
        self.checkConsistency('choice1')

if __name__ == '__main__':
    unittest.main()
