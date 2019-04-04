import os
import platform

import setuptools

# PYPY vs cpython
if platform.python_implementation() == 'PyPy':
    install_requires = ['psycopg2cffi>=2.7.2,<2.8']
else:
    install_requires = ['psycopg2>=2.5.1,<2.8']

# Install tornado if generating docs on readthedocs
if os.environ.get('READTHEDOCS', None) == 'True':
    install_requires.append('tornado')

setuptools.setup(
    name='queries',
    version='2.0.1',
    description='Simplified PostgreSQL client built upon Psycopg2',
    long_description=open('README.rst').read(),
    maintainer='Gavin M. Roy',
    maintainer_email='gavinmroy@gmail.com',
    url='https://github.com/gmr/queries',
    install_requires=install_requires,
    extras_require={'tornado': 'tornado<6'},
    license='BSD',
    package_data={'': ['LICENSE', 'README.rst']},
    packages=['queries'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries'],
    zip_safe=True)
