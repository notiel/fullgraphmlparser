import os
import stat
import subprocess
import shutil
import sys
import unittest

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
        return ['xvfb-run', os.path.abspath('~/qm/bin/qm.sh')]

    raise NotImplementedError('Only windows and linux are supported')

# Does full conversion cycle (C++ --> graphml --> qm --> C++)
@pytest.mark.skipif(sys.platform != "win32", reason="not yes sure how to install QM on other systems")
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
        parser = cpp_to_graphml.StateMachineParser(file_path = './testdata/oregonPlayer.cpp')
        parser.Parse()
        cpp_to_graphml.StateMachineWriter(parser).WriteToFile('./testdata/test_output/oregonPlayer.graphml')
        graphmltoqm.main('./testdata/test_output/oregonPlayer')
        subprocess.run(getQmWithArgs() + ['./testdata/test_output/oregonPlayer.qm', '-c'], check=True, timeout=10)
