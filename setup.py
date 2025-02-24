from setuptools import setup, find_packages

setup(
    name="betbuddy",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'python-dotenv',
        'requests',
    ],
) 