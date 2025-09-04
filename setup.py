from setuptools import setup, find_packages

setup(
    name='ie-requests',
    version='0.1.0',
    description='Consulta dados por IE ou CNPJ na SEFAZ-BA',
    author='Handlei Rodrigues',
    author_email='handlei.rodrigues@gmail.com',
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4'
    ],
)
