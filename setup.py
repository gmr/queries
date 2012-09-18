from setuptools import setup
import platform

# Make the install_requires
target = platform.python_implementation()
if target == 'PyPy':
    install_requires = ['psycopg2ct']
else:
    install_requires = ['psycopg2']

setup(name='pgsql_wrapper',
      version='1.1.2',
      description="PostgreSQL / psycopg2 caching wrapper class",
      maintainer="Gavin M. Roy",
      maintainer_email="gmr@meetme.com",
      url="http://github.com/MeetMe/pgsql_wrapper",
      install_requires=install_requires,
      py_modules=['pgsql_wrapper'],
      zip_safe=True)
