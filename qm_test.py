import unittest

from qm import *
from stateclasses import  *


class TriggersCreateTest(unittest.TestCase):

    def testEmptyTriggers(self):
        res, _ = create_actions(" ", "test", {})
        self.assertEqual(len(res), 0)

    def testEntryOnly(self):
        res, _ = create_actions("entry/\nBeepForPeriod(SHORT_BEEP_MS);\nFlash(127, 0, 0, FLASH_MS);\n\n"
                                "RAD_RCVD/\nBeepForPeriod(SHORT_BEEP_MS);\nFlash(127, 0, 0, FLASH_MS);", "test", {})
        self.assertEqual(len(res), 1)