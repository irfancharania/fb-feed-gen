# Facebook Feed Generator
[![Build Status](https://travis-ci.com/irfancharania/fb-feed-gen.svg?branch=master)](https://travis-ci.com/irfancharania/fb-feed-gen.svg?branch=master)

A number of organizations only provide regular updates through their Facebook pages and nowhere else. Up until recently, this wasn't a problem as Facebook provided RSS feeds for public-facing (non-login) pages. They dropped that feature at the end of June 2015.

This app generates Atom feeds so I can still get updates through my feed reader, without having to log into Facebook.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Run it Locally

```
virtualenv env -p `command -v python3`
env/bin/pip install -r requirements.txt
python setup.py install
fb-feedd-gen
```
Then go to http://127.0.0.1:5000

