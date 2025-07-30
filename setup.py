import setuptools
import glob

setuptools.setup(
        packages=['umbra'],
        scripts=glob.glob('bin/*'))
