from setuptools import setup
import platform

# Make the install_requires
target = platform.python_implementation()
if target == 'PyPy':
    install_requires = ['psycopg2ct']
else:
    install_requires = ['psycopg2']


setup(name='pgsql_wrapper',
      version='1.2.0',
      description="PostgreSQL / psycopg2 caching wrapper class",
      maintainer="Gavin M. Roy",
      maintainer_email="gavinmroy@gmail.com",
      url="https://github.com/gmr/pgsql_wrapper",
      install_requires=install_requires,
      license=open('LICENSE').read(),
      package_data={'': ['LICENSE', 'README.md']},
      py_modules=['pgsql_wrapper'],
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.2',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: Implementation :: CPython',
                   'Programming Language :: Python :: Implementation :: PyPy',
                   'Topic :: Database',
                   'Topic :: Software Development :: Libraries'],
      zip_safe=True)
