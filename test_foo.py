import codecs
import mock
import os
import shutil
import sys
import tempfile
import unittest
from argparse import Namespace

from foo import BashModule, Runner, main, re_parse_args


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self._log = mock.patch('foo.log')
        self.log = self._log.start()

    def tearDown(self):
        self.log.stop()


class ReParseArgsTestCase(BaseTestCase):

    def test_argument(self):
        for arg in ['argument', 'arg-ument', 'arg_ument']:
            rv = re_parse_args.match(arg)
            self.assertIsNotNone(rv)
            self.assertEquals(rv.groupdict()['argument'], arg)
            self.assertIsNone(rv.groupdict()['key'])
            self.assertIsNone(rv.groupdict()['key_name'])
            self.assertIsNone(rv.groupdict()['value'])
            self.assertIsNone(rv.groupdict()['lopt'])
            self.assertIsNone(rv.groupdict()['ropt'])

    def test_optional_argument(self):
        for arg in ['argument', 'arg-ument', 'arg_ument']:
            rv = re_parse_args.match('[%s]' % arg)
            self.assertIsNotNone(rv)
            self.assertEquals(rv.groupdict()['argument'], arg)
            self.assertEquals(rv.groupdict()['lopt'], '[')
            self.assertEquals(rv.groupdict()['ropt'], ']')
            self.assertIsNone(rv.groupdict()['key'])
            self.assertIsNone(rv.groupdict()['key_name'])
            self.assertIsNone(rv.groupdict()['value'])

    def test_key_value(self):
        for k, v in [('key', 'value'), ('k-ey', 'value'),
                     ('k_ey', 'value'), ('key', 'val-ue'),
                     ('key', 'val_ue'), ('k-ey', 'val-ue'),
                     ('k_ey', 'val_ue')]:
            rv = re_parse_args.match('--%s=%s' % (k, v))
            self.assertIsNotNone(rv)
            self.assertEquals(rv.groupdict()['key_name'], k)
            self.assertEquals(rv.groupdict()['key'], '--%s' % k)
            self.assertEquals(rv.groupdict()['value'], v)
            self.assertIsNone(rv.groupdict()['argument'])
            self.assertIsNone(rv.groupdict()['lopt'])
            self.assertIsNone(rv.groupdict()['ropt'])

    def test_optional_key_value(self):
        for k, v in [('key', 'value'), ('k-ey', 'value'),
                     ('k_ey', 'value'), ('key', 'val-ue'),
                     ('key', 'val_ue'), ('k-ey', 'val-ue'),
                     ('k_ey', 'val_ue')]:
            rv = re_parse_args.match('[--%s=%s]' % (k, v))
            self.assertIsNotNone(rv)
            self.assertEquals(rv.groupdict()['key_name'], k)
            self.assertEquals(rv.groupdict()['key'], '--%s' % k)
            self.assertEquals(rv.groupdict()['value'], v)
            self.assertEquals(rv.groupdict()['lopt'], '[')
            self.assertEquals(rv.groupdict()['ropt'], ']')
            self.assertIsNone(rv.groupdict()['argument'])

    def test_flag(self):
        for flag in ['flag', 'fla_g', 'fla-g']:
            rv = re_parse_args.match('--%s' % flag)
            self.assertIsNotNone(rv)
            self.assertEquals(rv.groupdict()['key_name'], flag)
            self.assertEquals(rv.groupdict()['key'], '--%s' % flag)
            self.assertIsNone(rv.groupdict()['argument'])
            self.assertIsNone(rv.groupdict()['value'])
            self.assertIsNone(rv.groupdict()['lopt'])
            self.assertIsNone(rv.groupdict()['ropt'])

    def test_optional_flag(self):
        for flag in ['flag', 'fla_g', 'fla-g']:
            rv = re_parse_args.match('[--%s]' % flag)
            self.assertIsNotNone(rv)
            self.assertEquals(rv.groupdict()['key_name'], flag)
            self.assertEquals(rv.groupdict()['key'], '--%s' % flag)
            self.assertEquals(rv.groupdict()['lopt'], '[')
            self.assertEquals(rv.groupdict()['ropt'], ']')
            self.assertIsNone(rv.groupdict()['argument'])
            self.assertIsNone(rv.groupdict()['value'])


class BashModuleTestCase(BaseTestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.tmpdir = tempfile.mkdtemp()
        self.module = os.path.join(self.tmpdir, 'module')

    def tearDown(self):
        super(BaseTestCase, self).tearDown()
        shutil.rmtree(self.tmpdir)

    def test_get_metadata(self):
        with codecs.open(self.module, 'w', 'utf-8') as fp:
            print >> fp, 'FOO_LOL=asdf'
            print >> fp, 'FOO_BAR="asdfa"'
            print >> fp, 'FOO_XD=1234'
            print >> fp, 'FOO_ASDF="1234"'
            print >> fp, 'FOO_HEHE="${FOO_ASDF}"'
            print >> fp, 'FOO_FUU=${FOO_BAR}'
            print >> fp, 'FOO_DFGDS'
            print >> fp, 'ASDF=XD'
            print >> fp
            print >> fp, 'main() { echo 1 }'
        obj = BashModule(self.module)
        meta = obj.get_metadata()
        self.assertEquals(meta['lol'], 'asdf')
        self.assertEquals(meta['bar'], 'asdfa')
        self.assertEquals(meta['xd'], '1234')
        self.assertEquals(meta['asdf'], '1234')
        self.assertEquals(meta['hehe'], '1234')
        self.assertEquals(meta['fuu'], 'asdfa')
        self.assertEquals(len(meta), 6)

    @mock.patch('foo.BashModule.get_metadata')
    def test_build_argparse(self, get_metadata):
        get_metadata.return_value = {'usage': ('foo --bar --baz=bah [asd] '
                                               '[--asdf] [--lol=hehe]'),
                                     'help': 'dummy', 'help_foo': 'foo1',
                                     'help_bar': 'bar2', 'help_baz': 'baz3',
                                     'help_asd': 'asd4', 'help_asdf': 'asdf5',
                                     'help_lol': 'lol6'}
        subparser = mock.Mock()
        obj = BashModule(self.module)
        parser = obj.build_argparse(subparser)
        subparser.add_parser.assert_called_once_with('module', help='dummy')
        self.assertEquals(parser.add_argument.call_args_list,
                          [mock.call('foo', help='foo1', nargs=1),
                           mock.call('--bar', required=True,
                                     action='store_const', const='1',
                                     help='bar2'),
                           mock.call('--baz', metavar='bah', required=True,
                                     help='baz3'),
                           mock.call('asd', help='asd4', nargs='?'),
                           mock.call('--asdf', required=False,
                                     action='store_const', const='1',
                                     help='asdf5'),
                           mock.call('--lol', metavar='hehe', required=False,
                                     help='lol6')])
        parser.set_defaults.called_once_with(_module=obj)

    @mock.patch('foo.BashModule.get_metadata')
    def test_build_argparse_with_invalid_arg(self, get_metadata):
        get_metadata.return_value = {'usage': ('foo1'),
                                     'help': 'dummy', 'help_foo1': 'foo1'}
        subparser = mock.Mock()
        obj = BashModule(self.module)
        with self.assertRaises(RuntimeError):
            obj.build_argparse(subparser)

    @mock.patch('foo.subprocess.Popen')
    def test_run(self, Popen):
        with codecs.open(self.module, 'w', 'utf-8') as fp:
            print >> fp, 'main() { echo 1 }'
        with mock.patch.dict('foo.os.environ',
                             {'PATH': '/', 'LC_ALL': 'en_US.utf8'},
                             clear=True):
            obj = BashModule(self.module)
            obj.run({'foo': 'bar', 'bar': ['baz'], 'lol': None})
        script = Popen.call_args[0][0][2]  # wtf?
        for func in ['log_debug', 'log_info', 'log_warning', 'log_error',
                     'log_critical']:
            self.assertIn('%s() {' % func, script)
        self.assertIn(self.module, script)
        env = Popen.call_args[1]['env']
        self.assertEquals(env['PATH'], '/')
        self.assertEquals(env['LC_ALL'], 'en_US.utf8')
        self.assertEquals(env['FOO_ARG_FOO'], 'bar')
        self.assertEquals(env['FOO_ARG_BAR'], 'baz')
        self.assertEquals(env['FOO_ARG_LOL'], '')
        self.assertEquals(len(env), 5)


class RunnerTestCase(BaseTestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.tmpdir = tempfile.mkdtemp()
        self.module = os.path.join(self.tmpdir, 'module')

    def tearDown(self):
        super(BaseTestCase, self).tearDown()
        shutil.rmtree(self.tmpdir)

    @mock.patch('foo.sysconfig.get_config_var')
    @mock.patch('foo.os.path.expanduser')
    def test_search_paths_not_created(self, expanduser, get_config_var):
        expanduser.return_value = self.tmpdir
        get_config_var.return_value = self.tmpdir
        runner = Runner()
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.assertEquals(runner.search_paths(),
                          [os.path.join(cwd, 'modules')])

    @mock.patch('foo.sysconfig.get_config_var')
    @mock.patch('foo.os.path.expanduser')
    def test_search_paths(self, expanduser, get_config_var):
        expanduser.return_value = self.tmpdir
        get_config_var.return_value = self.tmpdir
        runner = Runner()
        _cwd = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'modules')
        _user = os.path.join(self.tmpdir, '.local', 'libexec', 'foo-tools')
        if not os.path.isdir(_user):
            os.makedirs(_user)
        _global = os.path.join(self.tmpdir, 'libexec', 'foo-tools')
        if not os.path.isdir(_global):
            os.makedirs(_global)
        self.assertEquals(runner.search_paths(), [_user, _cwd, _global])

    @mock.patch('foo.Runner.search_paths')
    def test_modules(self, search_paths):
        _subdir = os.path.join(self.tmpdir, 'modules')
        if not os.path.isdir(_subdir):
            os.makedirs(_subdir)
        foo = os.path.join(self.tmpdir, 'foo')
        with open(foo, 'w') as fp:
            print >> fp
        bar = os.path.join(self.tmpdir, 'bar')
        with open(bar, 'w') as fp:
            print >> fp
        search_paths.return_value = [self.tmpdir, _subdir]
        runner = Runner()
        modules = runner.modules()
        self.assertIn('foo', modules)
        self.assertIn('bar', modules)

    @mock.patch('foo.Runner.search_paths')
    def test_duplicated_modules(self, search_paths):
        _subdir = os.path.join(self.tmpdir, 'modules')
        if not os.path.isdir(_subdir):
            os.makedirs(_subdir)
        foo = os.path.join(self.tmpdir, 'foo')
        with open(foo, 'w') as fp:
            print >> fp
        foo1 = os.path.join(self.tmpdir, 'foo')
        with open(foo1, 'w') as fp:
            print >> fp
        search_paths.return_value = [self.tmpdir, _subdir]
        runner = Runner()
        modules = runner.modules()
        self.assertIn('foo', modules)
        self.assertEquals(modules['foo'].fname, foo)

    @mock.patch('foo.Runner.modules')
    def test_run(self, modules):
        module = mock.Mock()
        modules.return_value = {'foo': module}
        runner = Runner()
        runner.parser = parser = mock.Mock()
        parser.parse_args.return_value = Namespace(foo='bar', bar=['baz'],
                                                   _lol='hehe', xd=None,
                                                   log_level='NOTSET',
                                                   _module=module)
        with mock.patch.object(sys, 'argv', ['foo', 'bar', '--traceback']):
            runner.run()
        module.build_argparse.assert_called_once_with(runner.subparser)
        parser.parse_args.assert_called_once_with(['bar'])
        module.run.assert_called_once_with({'bar': 'baz', 'foo': 'bar',
                                            'log_level': '0', 'xd': ''})


class MainTestCase(BaseTestCase):

    @mock.patch('foo.Runner')
    def test_ok(self, Runner):
        Runner.return_value = runner = mock.Mock()
        runner.run.return_value = 0
        self.assertEquals(main(), 0)
        Runner.assert_called_once_with()
        runner.run.assert_called_once_with()

    @mock.patch('foo.Runner')
    def test_with_exception(self, Runner):
        Runner.return_value = runner = mock.Mock()
        runner.run.side_effect = RuntimeError('foo')
        runner.run.return_value = 0
        self.assertEquals(main(), 1)

    @mock.patch('foo.Runner')
    def test_with_exception_reraised(self, Runner):
        Runner.return_value = runner = mock.Mock()
        runner.run.side_effect = RuntimeError('foo')
        runner.run.return_value = 0
        with mock.patch.object(sys, 'argv', ['foo', 'bar', '--traceback']):
            with self.assertRaises(RuntimeError):
                main()


if __name__ == '__main__':
    unittest.main()
