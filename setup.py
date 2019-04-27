from setuptools import find_packages, setup

setup(
    name='mailman',
    author='Daniel Besmer',
    author_email='besmerd@gmail.com',
    packages=find_packages(),
    use_scm_version=True,
    install_requires=[
        'jinja2',
        'pyyaml',
        'six',
    ],
    setup_requires=[
        'setuptools_scm'
    ],
    include_package_data=True,
    zip_safe=False,
    license="MIT",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    python_requires=">=3.6",
    entry_points='''
        [console_scripts]
        mailman=mailman.main:main
    ''',
)
