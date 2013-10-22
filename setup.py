from distutils.core import setup

setup(
    name='stoppark',
    version='0.6.16',
    author='feanor',
    author_email='std.feanor@gmail.com',
    packages=['stoppark'],
    package_data = {
       'stoppark': ['*.ui','*.png'],
    },
    scripts=[],
    url='https://github.com/stdk/stoppark_ext',
    license='LICENSE.txt',
    description='Stoppark project',
    long_description=open('README.txt').read(),
    install_requires=[
        "u2py >= 1.6.55.1"
    ],
)