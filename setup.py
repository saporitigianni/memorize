from setuptools import setup
from io import open


def readme():
    with open('README.rst', encoding='utf-8') as f:
        return '\n' + f.read()


MAJOR               = 0
MINOR               = 1
MICRO               = 1
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)


setup(name='memorize',
      version=VERSION,
      description='A caching package with options for timed caching and caching aware rate limiting',
      long_description=readme(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Internet',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: System :: Networking',
      ],
      keywords=[
          'cache',
          'caching',
          'decorator',
          'rate-limit',
          'timeout',
          'timer',
      ],
      url='https://github.com/saporitigianni/memorize',
      download_url='https://pypi.python.org/pypi/memorize',
      author='Gianni Saporiti',
      author_email='saporitigianni@outlook.com',
      python_requires='>=3',
      license='BSD',
      packages=['memorize'],
      install_requires=[],
      include_package_data=True,
      zip_safe=False)
