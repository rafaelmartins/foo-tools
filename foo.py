# -*- coding: utf-8 -*-
"""
    foo
    ~~~

    General purpose swiss-knife.

    :copyright: (c) 2013 by Rafael Goncalves Martins
    :license: BSD, see LICENSE for more details.
"""

__author__ = 'Rafael Goncalves Martins'
__email__ = 'rafael@rafaelmartins.eng.br'

__description__ = 'General purpose swiss-knife.'
__url__ = 'http://projects.rafaelmartins.eng.br/foo-tools/'
__copyright__ = '(c) 2013 %s <%s>' % (__author__, __email__)
__license__ = 'BSD'

__version__ = '0.1pre'

try:
    import argparse
except ImportError:  # Python 2.6, will be installed by setup.py
    pass
import logging
import os
import re
import shlex
import subprocess
import sys
import sysconfig

re_parse_args = re.compile(
    r'^(?P<lopt>\[)?('
    r'(?P<key>\-\-(?P<key_name>[a-z_-]+))(=(?P<value>[a-z_-]+))?|'
    r'(?P<argument>[a-z_-]+))'
    r'(?P<ropt>\])?$')

LOG_FORMAT = '%(name)s - %(levelname)s: %(message)s'

BASH_LIST_VARS = '''\
source "%(module)s" &> /dev/null
for i in $(compgen -A variable FOO_); do
    echo $i=\\""${!i}"\\"
done'''

BASH_LOGGING = '''\
log_%(levelname_lower)s() {
    if [[ ${FOO_ARG_LOG_LEVEL:-30} -le %(levelno)d ]]; then
        echo "%(name)s.%(modulename)s - %(levelname)s:" $@ >&2
    fi
}
'''

BASH_RUN_MODULE = '''\
die() {
    log_critical $@
    exit 1
}
source "%(module)s" > /dev/null
main'''

log = logging.getLogger('foo')
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
log.addHandler(_log_handler)
log.setLevel(logging.WARNING)


class BashModule(object):

    def __init__(self, fname):
        self.fname = fname
        self.name = os.path.basename(self.fname)

    def get_metadata(self):
        metadata = {}
        script = BASH_LIST_VARS % {'module': self.fname}
        rv = subprocess.check_output(['/bin/bash', '-c', script])
        for line in shlex.split(rv):
            pieces = line.split('=', 1)
            metadata[pieces[0].lower()[4:]] = pieces[1]
        return metadata

    def build_argparse(self, subparser):
        metadata = self.get_metadata()
        parser = subparser.add_parser(self.name, help=metadata.get('help'))
        for arg in shlex.split(metadata.get('usage', '')):
            rv = re_parse_args.match(arg)
            if rv is None:
                raise RuntimeError('Inconsistent argument: %s' % arg)
            args = rv.groupdict()
            optional = args['lopt'] == '[' and args['ropt'] == ']'
            if args['argument'] is not None:
                help = metadata.get('help_%s' % args['argument'].lower())
                parser.add_argument(args['argument'], help=help,
                                    nargs=optional and '?' or 1)
            elif args['key'] is not None:
                help = metadata.get('help_%s' % args['key_name'].lower())
                if args['value'] is not None:
                    parser.add_argument(args['key'], metavar=args['value'],
                                        required=not optional, help=help)
                else:
                    parser.add_argument(args['key'], required=not optional,
                                        action='store_const', const='1',
                                        help=help)
        parser.set_defaults(_module=self)
        return parser

    def run(self, args):
        env = {'PATH': os.environ['PATH']}
        # locale vars
        for var_name in os.environ:
            if var_name.startswith('LC_') or var_name in ['LANG', 'LANGUAGE']:
                env[var_name] = os.environ[var_name]
        for key, value in args.iteritems():
            if isinstance(value, list):
                value = value[0]
            if value is None:
                value = ''
            env['FOO_ARG_%s' % key.upper()] = value
        script = ''
        for levelno, levelname in logging._levelNames.iteritems():
            if not isinstance(levelname, basestring):
                continue
            if levelname == 'NOTSET':
                continue
            script += BASH_LOGGING % {'levelname': levelname,
                                      'levelname_lower': levelname.lower(),
                                      'levelno': levelno, 'name': 'foo',
                                      'modulename': self.name}
        script += BASH_RUN_MODULE % {'module': self.fname}
        proc = subprocess.Popen(['/bin/bash', '-c', script], env=env)
        return proc.wait()


class Runner(object):

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description=__description__)
        self.subparser = self.parser.add_subparsers(title='modules')
        self.parser.add_argument('--version', action='version',
                                 version='%%(prog)s %s' % __version__)
        self.parser.add_argument('--traceback', dest='_traceback',
                                 action='store_true',
                                 help='print Python traceback in errors, '
                                 'if possible.')
        levels = [j for i, j in logging._levelNames.iteritems()
                  if isinstance(j, basestring)]
        self.parser.add_argument('--log-level', dest='log_level',
                                 default='WARNING', choices=levels,
                                 help='configure logging level.')

    def search_paths(self):
        # The code below can't use any log level lower than WARNING
        paths = []
        _user = os.path.join(os.path.expanduser('~'), '.local', 'libexec',
                             'foo-tools')
        if os.path.isdir(_user):
            paths.append(_user)
        cwd = os.path.dirname(os.path.abspath(__file__))
        _local = os.path.join(cwd, 'modules')
        if os.path.isdir(_local):
            paths.append(_local)
        _egg = os.path.join(cwd, 'libexec', 'foo-tools')
        if os.path.isdir(_egg):
            paths.append(_egg)
        _global = os.path.join(sysconfig.get_config_var('base'), 'libexec',
                               'foo-tools')
        if os.path.isdir(_global):
            paths.append(_global)
        return paths

    def modules(self):
        # The code below can't use any log level lower than WARNING
        modules = {}
        for path in self.search_paths()[::-1]:
            for module in os.listdir(path):
                module_file = os.path.join(path, module)
                if os.path.isfile(module_file):
                    modules[module] = BashModule(module_file)
        return modules

    def run(self):
        modules = self.modules()
        for name in sorted(modules.keys()):
            modules[name].build_argparse(self.subparser)
        argv = sys.argv[1:]
        # ugly hack to avoid stupid argument ordering
        if '--traceback' in argv:
            argv.pop(argv.index('--traceback'))
        raw_args = self.parser.parse_args(argv)
        log.setLevel(logging._levelNames[raw_args.log_level])
        args = {}
        for arg in raw_args.__dict__:
            if arg.startswith('_'):  # private args
                continue
            value = getattr(raw_args, arg)
            if isinstance(value, list):
                value = value[0]
            if value is None:
                value = ''
            args[arg] = value
        if 'log_level' in args:
            args['log_level'] = str(logging._levelNames[args['log_level']])
        log.debug('Calling %s with arguments: %s' % (raw_args._module.name,
                                                     args))
        return raw_args._module.run(args)


def main():
    try:
        runner = Runner()
        return runner.run()
    except Exception, e:
        log.critical('%s: %s' % (e.__class__.__name__, str(e)))
        if '--traceback' in sys.argv:
            raise
    return 1


if __name__ == '__main__':
    sys.exit(main())
