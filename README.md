Quickstart
==========

Using virtualenv
----------------

Initialize a virtualenv and install cloaca.
    
    virtualenv --no-site-packages venv.cloaca
    source venv.cloaca/bin/activate
    (venv.cloaca) git clone https://github.com/mhmurray/cloaca.git
    (venv.cloaca) cd cloaca/
    (venv.cloaca) python setup.py install

Set up a [Redis instance](http://redis.io/topics/quickstart), on port 6379.

Run the server on localhost:8080 without SSL
    
    (venv.cloaca) cloacaapp.py --port 8080 --no-ssl

Point your browser to localhost:8080.


Caveats
-------
This is still in early testing. No promises about proper web security.
Also don't run this against a Redis instance you care about. cloacaapp.py
does support Redis's SELECT to pick a database, but there is no 
support for a key prefix to avoid clobbering other stored keys.
