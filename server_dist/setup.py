from setuptools import setup, find_packages

setup(name="gb_test_server",
      version="0.0.1",
      description="PyQt messenger Server",
      author="Klark Charlz",
      author_email="klark.charlz@mail.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex'],
      )
