# vim:ts=4:sts=4:sw=4:expandtab

import unittest

from kolejka.common.limits import KolejkaLimits, KolejkaStats 

class TestStats(unittest.TestCase):
    def test_sum(self):
        stats = KolejkaStats(cpu={'usage':'1s', 'system':'5s', 'user':'1s'},
                    cpus = {
                        '0' : {'usage':'1s', 'system':'2s', 'user':'1s'},
                        '1' : {'usage':'1s', 'system':'2s', 'user':'1s'},
                    }
                )
        self.assertEqual(stats.cpu.usage.total_seconds(), 7.0)
        self.assertEqual(stats.cpu.system.total_seconds(), 5.0)
        self.assertEqual(stats.cpu.user.total_seconds(), 2.0)

if __name__ == '__main__':
    unittest.main()
