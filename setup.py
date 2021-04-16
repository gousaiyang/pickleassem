import os

from setuptools import setup  # type: ignore[import]

os.chdir(os.path.dirname(os.path.realpath(__file__)))

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pickleassem',
    version='1.0.0',
    description='A simple pickle assembler to make handcrafting pickle bytecode easier.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/gousaiyang/pickleassem',
    author='Saiyang Gou',
    author_email='gousaiyang223@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Security',
        'Topic :: Software Development :: Assemblers',
        'Topic :: Utilities',
    ],
    keywords='pickle assembler handcraft bytecode security exploit ctf',
    py_modules=['pickleassem'],
    python_requires='>=3.4',
    install_requires=[
        'typing;python_version<"3.5"',
        'typing_extensions>=3.7.2',
    ],
)
