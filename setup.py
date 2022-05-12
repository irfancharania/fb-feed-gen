import sys
from setuptools import setup

if sys.version_info < (3, 7):
    sys.exit('Sorry, Python < 3.7 is not supported')

install_requires = list(val.strip() for val in open('requirements.txt'))

setup(name='fb-feed-gen',
      version='0.1.0',
      description='Facebook Feed Generator',
      author='Irfan Charania',
      author_email='',
      url='https://github.com/irfancharania/fb-feed-gen',
      packages=['fb_feed_gen'],
      entry_points={
            'console_scripts': [
                 'fb-feed-gen = fb_feed_gen.app:main',
            ]
      },
      include_package_data=True,
      data_files=[('static/css', ['static/css/style.css']),
                  ('static/ico', ['static/ico/favicon.ico']),
                  ('templates', ['templates/index.html'])],
      license='GPL 2.0',
      install_requires=install_requires,
      classifiers=[
         'Programming Language :: Python :: 3.7',
         'Programming Language :: Python :: 3.8',
      ]
)
