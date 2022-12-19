import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
        name="guppi",
        version="1.0.1",
        author="Wael Farah",
        author_email="wael.a.farah@gmail.com",
        url='',
        description='A simple Guppi RAW multi-antenna reader',
        install_requires=['numpy'],
        packages=['guppi']
)
