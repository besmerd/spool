from setuptools import setup, find_packages

setup(
    name='hermodr',
    author='Daniel Besmer',
    author_email='besmerd@gmail.com',
    packages=find_packages(),
    use_scm_version=True,
    install_requires=[
        'jinja2',
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
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    python_requires=">=3.4",
    entry_points='''
        [console_scripts]
        hermodr=hermodr.main:main
    ''',
)
