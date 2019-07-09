import sys
import unittest
from unittest.mock import patch
from unittest.mock import MagicMock

class TestStringMethods(unittest.TestCase):

    def testNumberOfStates(self):
        with patch.object(sys, 'argv', ['.', './testdata/oregonPlayer.cpp']):
            import cpp_to_graphml
            self.assertEqual(len(cpp_to_graphml.parser.states), 15)

if __name__ == '__main__':
    unittest.main()