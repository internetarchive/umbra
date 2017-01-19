import setuptools
import glob

setuptools.setup(
        name='umbra',
        version='2.0.dev8',
        description='Browser automation via chrome debug protocol',
        url='https://github.com/internetarchive/umbra',
        author='Eldon Stegall',
        author_email='eldon@archive.org',
        long_description=open('README.md').read(),
        license='Apache License 2.0',
        packages=['umbra'],
        install_requires=['brozzler>1.1b8', 'kombu==3.0.37', 'PyYAML'],
        scripts=glob.glob('bin/*'),
        zip_safe=False,
        classifiers=[
            'Environment :: Console',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 3.4',
            'Topic :: System :: Archiving',
        ])
