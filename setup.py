from setuptools import setup, find_packages
import os

# parse __version__ from version.py
exec(open('friendlyfred/version.py').read())

# parse long_description from README.rst
with open("README.rst", "r") as fh:
    long_description = fh.read()

# we conditionally add python-snappy based on the presence of an env var
dependencies = ['pandas', 'anytree', 'lxml', 'urllib3', 'tqdm']
rtd_build_env = os.environ.get('READTHEDOCS', False)
if not rtd_build_env:
    with open('requirements.txt') as fh:
        dependencies = fh.read().splitlines()
dependencies = [x for x in dependencies if not x.startswith('#')]

setup(
  name = 'friendlyfred',
  packages = find_packages(),
  version = __version__,
  license='MIT',
  description = "FRED data API wrapper for Python",
  long_description=long_description,
  long_description_content_type="text/markdown",
  author = 'Danil Zherebtsov',
  author_email = 'danil.com@me.com',
  url = 'https://github.com/DanilZherebtsov/friendlyfred',
  download_url = 'https://github.com/DanilZherebtsov/friendlyfred/archive/refs/tags/0.1.2.tar.gz',
  keywords = ['fred', 'economics', 'macroeconomic', 'data'],
  install_requires=dependencies,
  classifiers=[
  'Development Status :: 4 - Beta',
  'Intended Audience :: Developers',
  'Topic :: Software Development :: Build Tools',
  'License :: OSI Approved :: MIT License',
  'Programming Language :: Python :: 3.7',
  'Programming Language :: Python :: 3.8',
  'Programming Language :: Python :: 3.9',
  'Programming Language :: Python :: 3.10',
  'Programming Language :: Python :: 3.11'
  ]
)
