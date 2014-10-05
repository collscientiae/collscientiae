from distutils.core import setup
from collscientia import __version__
r"""
CollScientia -- Collection of Knowledge

"""

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
    long_description=__doc__,
    install_requires=open("requirements.txt").readlines(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
)
