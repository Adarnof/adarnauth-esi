import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='adarnauth-esi',
    version='1.1.1',
    install_requires=[
        'requests>=2.9.1',
        'requests_oauthlib',
        'django>=1.10',
        'bravado>=8.4.0',
        'django-celery',
    ],
    packages=find_packages(),
    include_package_data=True,
    license='GNU GPLv3',
    description='Django app for accessing the EVE Swagger Interface.',
    long_description=README,
    url='https://adarnauth.tech/',
    author='Adarnof',
    author_email='adarnof@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU GPLv3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
