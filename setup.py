from setuptools import setup, find_packages
from pyclarity_lims.version import __version__
import subprocess

# Fetch version from git tags.
# if git is not available (PyPi package), use stored version.py.

try:
    version = subprocess.Popen(["git", "describe", "--abbrev=0"], stdout=subprocess.PIPE, universal_newlines=True).communicate()[0].rstrip()
    version = version.decode("utf-8")
except:
    version = __version__

try:
    with open("requirements.txt") as rq:
        requires=rq.readlines()
except:
    requires=["requests"]

setup(name='pyclarity_lims',
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
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
      "requests"
    ],

)
