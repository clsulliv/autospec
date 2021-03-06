import os
import tempfile
import unittest
from unittest.mock import mock_open, patch
import test


def mock_generator(rv=None):
    def mock_f(*args, **kwargs):
        return rv

    return mock_f


class TestTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.open_name = 'test.open'
        test.config.config_opts['skip_tests'] = False
        test.config.config_opts['allow_test_failures'] = False
        test.os.path.isfile = mock_generator(True)

    def setUp(self):
        test.tests_config = ''
        test.tarball.name = ''
        test.buildreq.buildreqs = set()
        test.buildpattern.default_pattern = "make"

    def test_check_regression(self):
        """
        Test check_regression
        """
        def mock_parse_log(log):
            return ',120,100,20,0,0'

        parse_log_backup = test.count.parse_log
        test.count.parse_log = mock_parse_log
        m_open = mock_open()
        open_name = 'util.open'
        with patch(open_name, m_open, create=True):
            test.check_regression('pkgdir')

        exp_call = unittest.mock.call().write('Total : 120\n'
                                              'Pass : 100\n'
                                              'Fail : 20\n'
                                              'Skip : 0\n'
                                              'XFail : 0\n')
        self.assertIn(exp_call, m_open.mock_calls)

    def test_check_regression_multi(self):
        """
        Test check_regression with multiple results
        """
        def mock_parse_log(log):
            return 'test-a,120,100,20,0,0\ntest-b,10,5,3,2,1'

        parse_log_backup = test.count.parse_log
        test.count.parse_log = mock_parse_log
        m_open = mock_open()
        open_name = 'util.open'
        with patch(open_name, m_open, create=True):
            test.check_regression('pkgdir')

        exp_call = unittest.mock.call().write('Package : test-a\n'
                                              'Total : 120\n'
                                              'Pass : 100\n'
                                              'Fail : 20\n'
                                              'Skip : 0\n'
                                              'XFail : 0\n'
                                              'Package : test-b\n'
                                              'Total : 10\n'
                                              'Pass : 5\n'
                                              'Fail : 3\n'
                                              'Skip : 2\n'
                                              'XFail : 1\n')
        self.assertIn(exp_call, m_open.mock_calls)

    def test_scan_for_tests_makecheck_in(self):
        """
        Test scan_for_tests with makecheck suite
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['Makefile.in'])
        content = 'check:'
        m_open = mock_open(read_data=content)
        with patch(self.open_name, m_open, create=True):
            test.buildpattern.default_pattern = "configure"
            test.scan_for_tests('pkgdir')

        test.os.listdir = listdir_backup
        test.buildpattern.default_pattern = "make"
        self.assertEqual(test.tests_config,
                         'make VERBOSE=1 V=1 %{?_smp_mflags} check')

    def test_scan_for_tests_makecheck_am(self):
        """
        Test scan_for_tests with makecheck suite via Makefile.am
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['Makefile.am'])
        m_open = mock_open()
        with patch(self.open_name, m_open, create=True):
            test.buildpattern.default_pattern = "configure_ac"
            test.scan_for_tests('pkgdir')

        test.os.listdir = listdir_backup
        test.buildpattern.default_pattern = "make"
        self.assertEqual(test.tests_config,
                         'make VERBOSE=1 V=1 %{?_smp_mflags} check')

    def test_scan_for_tests_perlcheck_PL(self):
        """
        Test scan_for_tests with perlcheck suite
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['Makefile.PL'])
        test.buildpattern.default_pattern = "cpan"
        test.scan_for_tests('pkgdir')
        test.os.listdir = listdir_backup
        test.buildpattern.default_pattern = "make"
        self.assertEqual(test.tests_config, 'make TEST_VERBOSE=1 test')

    def test_scan_for_tests_perlcheck_in(self):
        """
        Test scan_for_tests with perlcheck suite via Makefile.in
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['Makefile.in'])
        content = 'test:'
        m_open = mock_open(read_data=content)
        with patch(self.open_name, m_open, create=True):
            test.buildpattern.default_pattern = "cpan"
            test.scan_for_tests('pkgdir')

        test.os.listdir = listdir_backup
        test.buildpattern.default_pattern = "make"
        self.assertEqual(test.tests_config, 'make TEST_VERBOSE=1 test')

    def test_scan_for_tests_setup(self):
        """
        Test scan_for_tests with setup.py suite
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['setup.py'])
        content = 'test_suite'
        m_open = mock_open(read_data=content)
        with patch(self.open_name, m_open, create=True):
            test.buildpattern.default_pattern = "distutils3"
            test.scan_for_tests('pkgdir')

        test.os.listdir = listdir_backup
        test.buildpattern.default_pattern = "make"
        self.assertEqual(test.tests_config,
                         'PYTHONPATH=%{buildroot}/usr/lib/python3.7/site-packages '
                         'python3 setup.py test')

    def test_scan_for_tests_cmake(self):
        """
        Test scan_for_tests with cmake suite
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['CMakeLists.txt'])
        content = 'enable_testing'
        m_open = mock_open(read_data=content)
        with patch(self.open_name, m_open, create=True):
            test.buildpattern.default_pattern = "cmake"
            test.scan_for_tests('pkgdir')

        test.os.listdir = listdir_backup
        test.buildpattern.default_pattern = "make"
        self.assertEqual(test.tests_config,
                         'cd clr-build; make test')

    def test_scan_for_tests_tox_requires(self):
        """
        Test scan_for_tests with tox.ini in the files list, should add several
        build requirements
        """
        listdir_backup = os.listdir
        test.os.listdir = mock_generator(['tox.ini'])
        test.scan_for_tests('pkgdir')
        test.os.listdir = listdir_backup
        self.assertEqual(test.buildreq.buildreqs,
                         set(['tox',
                              'pytest',
                              'virtualenv',
                              'pluggy',
                              'py-python']))


if __name__ == "__main__":
    unittest.main(buffer=True)
