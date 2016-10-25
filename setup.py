from setuptools import setup
import os
import platform

# Include the proper requirements
if platform.python_implementation() == 'PyPy':
    install_requires = ['psycopg2cffi>=2.7.2,<3']
else:
    install_requires = ['psycopg2>=2.5.1,<3']

# Install tornado if generating docs on readthedocs
if os.environ.get('READTHEDOCS', None) == 'True':
    install_requires.append('tornado')

classifiers = ['Development Status :: 5 - Production/Stable',
               'Intended Audience :: Developers',
               'License :: OSI Approved :: BSD License',
               'Operating System :: OS Independent',
               'Programming Language :: Python :: 2',
               'Programming Language :: Python :: 2.6',
               'Programming Language :: Python :: 2.7',
               'Programming Language :: Python :: 3',
               'Programming Language :: Python :: 3.3',
               'Programming Language :: Python :: 3.4',
               'Programming Language :: Python :: 3.5',
               'Programming Language :: Python :: Implementation :: CPython',
               'Programming Language :: Python :: Implementation :: PyPy',
               'Topic :: Database',
               'Topic :: Software Development :: Libraries']

setup(name='queries',
      version='1.9.1',
      description="Simplified PostgreSQL client built upon Psycopg2",
      maintainer="Gavin M. Roy",
      maintainer_email="gavinmroy@gmail.com",
      url="https://github.com/gmr/queries",
      install_requires=install_requires,
      extras_require={'tornado': 'tornado'},
      license=open('LICENSE').read(),
      package_data={'': ['LICENSE', 'README.rst']},
      packages=['queries'],
      classifiers=classifiers,
      zip_safe=True)
