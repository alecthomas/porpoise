import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='Porpoise',
    version='0.1.0',
    url='https://github.com/alecthomas/porpoise',
    license='BSD',
    author='Alec Thomas',
    author_email='alec@swapoff.org',
    description='A Redis-based analytics framework.',
    py_modules=['porpoise'],
    zip_safe=True,
    platforms='any',
    install_requires=['redis'],
    cmdclass={'test': PyTest},
)
