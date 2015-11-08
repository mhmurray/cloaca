Packages needed

* zope (https://pypi.python.org/pypi/zope.interface)
* twisted (https://twistedmatrix.com/)
* urwid (http://urwid.org/)

installation steps:

* Ubuntu package requirements: python-twisted, python-urwid, python-zope.interface
* add the directory that contains this package to your python path. Eg.
    
        mkdir ~/cloaca
        cd ~/cloaca
        git clone https://github.com/mhmurray/cloaca.git

  Add ~/cloaca/ to PYTHONPATH env variable, eg.

        export PYTHONPATH=$PYTHONPATH:$HOME/cloaca

* Run the server using the .tac file and twistd, which
  starts a server on port 5000

        twistd -ny twisted-server.tac

* Connect with a client in a separate terminal.

        ./twisted-client3.py --port 5000 my_username

Installation on Mac

* Mac Yosemite June 2015. Installed twisted & zope.
