from setuptools import find_packages, setup

setup(
    name='mailman',
    author='Daniel Besmer',
    author_email='besmerd@gmail.com',
    packages=find_packages(),
    use_scm_version=True,
    install_requires=[
        'cerberus',
        'M2Crypto',
        'dkimpy',
        'jinja2',
        'pyyaml',
    ],
    setup_requires=[
        'setuptools_scm'
    ],
    tests_require=[
        'pytest',
    ],
    include_package_data=True,
    zip_safe=False,
    license="MIT",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires=">=3.6",
    entry_points='''
        [console_scripts]
        mailman=mailman.main:cli
    ''',
)
