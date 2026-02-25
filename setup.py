from setuptools import setup, find_packages

setup(
    name='gluex.jupyroot',
    version='1.0.22',
    packages=['gluex.jupyroot'],
    install_requires=[
        "dask",
        "distributed",
        "cloudpickle",
        "numpy",
        "psutil",
        "ipython",
        "gluex.hddm_s",
        "gluex.hddm_r",
    ],
    description='Automate common data analysis and visualization tasks using the CERN pyroot library in a jupyter notebook.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rjones30/jupyroot',
    author='Richard Jones',
    author_email='richard.t.jones@uconn.edu',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
