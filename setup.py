from os.path import join, abspath, dirname
from setuptools import setup, find_packages


requirements_txt = join(abspath(dirname(__file__)), 'requirements.txt')
requirements = [l.strip() for l in open(requirements_txt) if l and not l.startswith('#')]

version = '0.4.7'


setup(
    name='pyclarity_lims',
    version=version,
    description="Python interface to the Basespace-Clarity LIMS (Laboratory Information Management System) "
                "server via its REST API.",
    long_description="""A basic module for interacting with the Basespace-Clarity LIMS server via its REST API.
                      The goal is to provide simple access to the most common entities and their attributes in
                      a reasonably Pythonic fashion.""",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering :: Medical Science Apps."
    ],
    keywords='clarity api rest',
    author='Per Kraulis',
    author_email='per.kraulis@scilifelab.se',
    maintainer='Timothee Cezard',
    maintainer_email='timothee.cezard@ed.ac.uk',
    url='https://github.com/EdinburghGenomics/pyclarity-lims',
    license='GPLv3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests', 'integration_tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=['requests']
)
