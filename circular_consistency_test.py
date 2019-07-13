import sys
import unittest

import pytest

import cpp_to_graphml
import graphmltoqm


# Does full conversion cycle (C++ --> graphml --> qm --> C++)
@pytest.mark.skipif(sys.platform != "win32", reason="not yes sure how to install QM on other systems")
class CircularConsistencyTest(unittest.TestCase):
    def testFullCycle(self):
        parser = cpp_to_graphml.StateMachineParser(file_path = './testdata/oregonPlayer.cpp')
        parser.Parse()
        cpp_to_graphml.StateMachineWriter(parser).WriteToFile('./testdata/oregonPlayer.graphml')
        graphmltoqm.main('./testdata/oregonPlayer')