import setuptools
import glob

setuptools.setup(
        name='umbra',
        version='2.1.dev10',
        description='Browser automation via chrome debug protocol',
        url='https://github.com/internetarchive/umbra',
        author='Eldon Stegall',
        author_email='eldon@archive.org',
        long_description=open('README.md').read(),
        license='Apache License 2.0',
        packages=['umbra'],
        install_requires=[
            'brozzler>=1.6.10',
            'kombu>=5.3.3, <6',
            'PyYAML'
        ],
        scripts=glob.glob('bin/*'),
        zip_safe=False,
        classifiers=[
            'Environment :: Console',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 3.4',
            'Topic :: System :: Archiving',
        ])
