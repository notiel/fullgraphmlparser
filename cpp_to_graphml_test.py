import sys
import unittest

import cpp_to_graphml


class TestStringMethods(unittest.TestCase):

    def testNumberOfStates(self):
        parser = cpp_to_graphml.StateMachineParser(file_path = './testdata/oregonPlayer.cpp')
        parser.Parse()
        self.assertEqual(len(parser.states), 15)

if __name__ == '__main__':
    unittest.main()
