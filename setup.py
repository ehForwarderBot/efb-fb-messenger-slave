import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 6):
    raise Exception("Python 3.6 or higher is required. Your version is %s." % sys.version)

__version__ = ""
exec(open('efb_fb_messenger_slave/__version__.py').read())

long_description = open('README.rst').read()

setup(
    name='efb-fb-messenger-slave',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    version=__version__,
    description='Facebook Messenger Slave Channel for EH Forwarder Bot, based on ``fbchat``.',
    long_description=long_description,
    author='Eana Hufwe',
    author_email='ilove@1a23.com',
    url='https://github.com/blueset/efb-fb-messenger-slave',
    license='AGPLv3+',
    include_package_data=True,
    python_requires='>=3.6',
    keywords=['ehforwarderbot', 'EH Forwarder Bot', 'EH Forwarder Bot Master Channel',
              'facebook messenger', 'messenger', 'chatbot'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities"
    ],
    install_requires=[
        "ehforwarderbot",
        "fbchat",
        "PyYaml",
        'requests',
        'emoji'
    ],
    entry_points={
        "console_scripts": ["efms-auth = efb_fb_messenger_slave.__main__:main"],
        "ehforwarderbot.slave": ["blueset.fbmessenger = efb_fb_messenger_slave:FBMessengerChannel"]
    }
)
