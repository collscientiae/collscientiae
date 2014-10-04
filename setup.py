from distutils.core import setup
from collscientia import __version__

setup(
    name='collscientia',
    version=__version__,
    packages=['collscientia'],
    test_suite='nose.collector',
    url='',
    license='LICENSE.txt',
    author='Harald Schilly',
    author_email='harald@schil.ly',
    description='Collection of Knowledge: ' +
    'an advanced system for building modularized documentations',
    install_requires = open("requirements.txt").readlines()
)
