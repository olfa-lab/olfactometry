__author__ = 'chris'

from distutils.core import setup

files = []

setup(name='olfactometry',
      version='0.1dev',
      description="runs olfactometer devices from rinberg lab",
      author='Rinberg Lab',
      packages=['olfactometry'], requires=['matplotlib', 'PyQt4', 'scipy', 'numpy']
      )