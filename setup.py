from setuptools import setup, find_packages

setup(
    name='jupyroot',  # Name of the package
    version='1.0.0',
    packages=find_packages(),  # Automatically find packages in the jupyroot/ directory
    install_requires=[],  # Add dependencies here if any
    description='Automate common data analysis and visualization tasks using the CERN pyroot library in a jupyter notebook.'
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rjones30/jupyroot',
    author='Richard Jones',
    author_email='richard.t.jones@uconn.edu',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
