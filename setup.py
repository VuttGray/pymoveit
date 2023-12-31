from setuptools import setup, find_packages
from os.path import join, dirname
import pymoveit


def get_requirements():
    """Collect the requirements list for the package"""
    requirements = []
    with open('requirements.txt') as f:
        for requirement in f:
            requirements.append(requirement.strip())
    return requirements


def main():
    requirements = get_requirements()
    setup(
        name=pymoveit.__name__,
        version=pymoveit.__version__,
        author='Denis Stepanov',
        author_email='vutt.gray@gmail.com',
        packages=find_packages(),
        long_description=open(join(dirname(__file__), 'README.md')).read(),
        install_requires=requirements,
        )


if __name__ == "__main__":
    main()
