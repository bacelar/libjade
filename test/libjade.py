import glob
import os
from typing import Optional
from functools import lru_cache, reduce

import yaml
import platform
import helpers

#GITROOT = reduce(os.path.join, helpers.run_subprocess(['git', 'rev-parse', '--show-toplevel'], print_output=False).strip().split(os.sep), os.sep)
GITROOT = helpers.run_subprocess(['git', 'rev-parse', '--show-toplevel'], print_output=False).strip()
SRC = os.path.join(GITROOT, 'src')

class Scheme:
    def __init__(self):
        self.type = None
        self.name = None
        self.name_ = None
        self.implementations = []

    def path(self, base=SRC):
        return os.path.join(base, 'crypto_' + self.type, self.name)

    def namespace_prefix(self):
        return 'LIBJADE_{}_'.format(self.name.upper()).replace('-', '')

    @staticmethod
    @lru_cache(maxsize=None)
    def by_name(scheme_name):
        for scheme in Scheme.all_schemes():
            if scheme.name == scheme_name:
                return scheme
        raise KeyError()

    @staticmethod
    @lru_cache(maxsize=1)
    def all_schemes():
        schemes = []
        schemes.extend(Scheme.all_schemes_of_type('kem'))
        schemes.extend(Scheme.all_schemes_of_type('stream'))
        schemes.extend(Scheme.all_schemes_of_type('onetimeauth'))
        schemes.extend(Scheme.all_schemes_of_type('hash'))
        schemes.extend(Scheme.all_schemes_of_type('xof'))
        schemes.extend(Scheme.all_schemes_of_type('sign'))
        schemes.extend(Scheme.all_schemes_of_type('scalarmult'))
        return schemes

    @staticmethod
    @lru_cache(maxsize=1)
    def all_implementations():
        implementations = []
        for scheme in Scheme.all_schemes():
            implementations.extend(scheme.implementations)
        return implementations

    @staticmethod
    @lru_cache(maxsize=1)
    def all_supported_implementations():
        return [impl for impl in Scheme.all_implementations()
                if impl.supported_on_current_platform()]

    @staticmethod
    @lru_cache(maxsize=32)
    def all_schemes_of_type(type: str) -> list:
        schemes = []
        p = os.path.join(SRC, 'crypto_' + type)
        if os.path.isdir(p):
            cleaner = lambda d: os.path.relpath(os.path.dirname(d), p)
            metas = glob.glob(os.path.join(p, '**', 'META.yml'), recursive=True)
            scheme_names = list( map( cleaner, metas ))
            for d in scheme_names:
                if os.path.isdir(os.path.join(p, d)):
                    if type == 'kem':
                        schemes.append(KEM(d))
                    elif type == 'stream':
                        schemes.append(Stream(d))
                    elif type == 'onetimeauth':
                        schemes.append(Onetimeauth(d))
                    elif type == 'hash':
                        schemes.append(Hash(d))
                    elif type == 'xof':
                        schemes.append(Xof(d))
                    elif type == 'sign':
                        schemes.append(Signature(d))
                    elif type == 'scalarmult':
                        schemes.append(Scalarmult(d))
                    else:
                        assert('Unknown type')
        return schemes

    @lru_cache(maxsize=None)
    def metadata(self):
        metafile = os.path.join(self.path(), 'META.yml')
        try:
            with open(metafile, encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
            return metadata
        except Exception as e:
            print("Can't open {}: {}".format(metafile, e))
            return None

    def __repr__(self):
        return "<{}({})>".format(self.type.title(), self.name)


class Implementation:

    def __init__(self, scheme, name):
        self.scheme = scheme
        self.name = name
        self.name_ = name.replace(os.sep, '_')

    @lru_cache(maxsize=None)
    def metadata(self):
        for i in self.scheme.metadata()['implementations']:
            if i['name'] == self.name:
                return i

    def path(self, base=SRC) -> str:
        return os.path.join(self.scheme.path(base=base), self.name)

    def libname(self) -> str:
        if os.name == 'nt':
            return "lib{}_{}.lib".format(self.scheme.name, self.name)
        return "lib{}_{}.a".format(self.scheme.name, self.name)

    def cfiles(self) -> [str]:
        return glob.glob(os.path.join(self.path(), '*.c'))

    def hfiles(self) -> [str]:
        return glob.glob(os.path.join(self.path(), '*.h'))

    def ofiles(self) -> [str]:
        return glob.glob(os.path.join(self.path(),
                         '*.o' if os.name != 'nt' else '*.obj'))

    @staticmethod
    @lru_cache(maxsize=None)
    def by_name(scheme_name, implementation_name):
        scheme = Scheme.by_name(scheme_name)
        for implementation in scheme.implementations:
            if implementation.name == implementation_name:
                return implementation
        raise KeyError()

    @staticmethod
    @lru_cache(maxsize=None)
    def all_implementations(scheme: Scheme) -> list:
        implementations = []
        p = scheme.path()
        impl_names = list(map(lambda d: os.path.relpath(os.path.dirname(d), p), \
                              glob.glob(os.path.join(p, '**/'+scheme.type+'.jazz'),recursive=True)))
        for d in impl_names:
            if os.path.isdir(os.path.join(scheme.path(), d)):
                implementations.append(Implementation(scheme, d))
        return implementations

    @staticmethod
    def all_supported_implementations(scheme: Scheme) -> list:
        return [impl for impl in Implementation.all_implementations(scheme)
                if impl.supported_on_current_platform()]

    def namespace_prefix(self):
        return '{}{}_'.format(self.scheme.namespace_prefix(),
                              self.name.upper()).replace('-', '')

    def supported_on_os(self, os: Optional[str] = None) -> bool:
        """Check if we support the OS

        If no OS is specified, then we run on the current OS
        """
        if os is None:
            os = platform.system()

        for platform_ in self.metadata().get('supported_platforms', []):
            if 'operating_systems' in platform_:
                if os not in platform_['operating_systems']:
                    return False

        return True

    @lru_cache(maxsize=10000)
    def supported_on_current_platform(self) -> bool:
        if 'supported_platforms' not in self.metadata():
            return True

        if platform.machine() == 'ppc':
            return False

        if not self.supported_on_os():
            return False

        cpuinfo = helpers.get_cpu_info()

        for platform_ in self.metadata()['supported_platforms']:
            if platform_['architecture'] == cpuinfo['arch'].lower():
                # Detect actually running on emulated i386
                if (platform_['architecture'] == 'x86_64' and
                        platform.architecture()[0] == '32bit'):
                    continue
                if not 'required_flags' in platform_:
                   return True
                if all([flag in cpuinfo['flags']
                        for flag in platform_['required_flags']]):
                    return True
        return False

    def __str__(self):
        return "{} implementation of {}".format(self.name, self.scheme.name)

    def __repr__(self):
        return "<Implementation({}, {})>".format(self.scheme.name, self.name)


class KEM(Scheme):
    def __init__(self, name: str):
        self.type = 'kem'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_kems() -> list:
        return Scheme.all_schemes_of_type('kem')

class Stream(Scheme):
    def __init__(self, name: str):
        self.type = 'stream'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_stream() -> list:
        return Scheme.all_schemes_of_type('stream')

class Onetimeauth(Scheme):
    def __init__(self, name: str):
        self.type = 'onetimeauth'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_onetimeauth() -> list:
        return Scheme.all_schemes_of_type('onetimeauth')

class Hash(Scheme):
    def __init__(self, name: str):
        self.type = 'hash'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_hash() -> list:
        return Scheme.all_schemes_of_type('hash')

class Xof(Scheme):
    def __init__(self, name: str):
        self.type = 'xof'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_xof() -> list:
        return Scheme.all_schemes_of_type('xof')

class Signature(Scheme):

    def __init__(self, name: str):
        self.type = 'sign'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_sigs():
        return Scheme.all_schemes_of_type('sign')

class Scalarmult(Scheme):

    def __init__(self, name: str):
        self.type = 'scalarmult'
        self.name = name
        self.name_ = name.replace(os.sep, '_')
        self.implementations = Implementation.all_implementations(self)

    @staticmethod
    def all_scalarmult():
        return Scheme.all_schemes_of_type('scalarmult')
