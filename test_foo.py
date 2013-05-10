import codecs
import mock
import os
import shutil
import tempfile
import unittest

from foo import BashModule, re_parse_args


class ReParseArgsTestCase(unittest.TestCase):

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


class BashModuleTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.module = os.path.join(self.tmpdir, 'module')

    def tearDown(self):
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


if __name__ == '__main__':
    unittest.main()
