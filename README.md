Please see the wiki for more information about ongoing development!

https://github.com/mhmurray/cloaca/wiki

# Terminal colors

Terminal colors can be provided using the termcolor python package.
It provides utility functions to insert ANSI escape sequences that
colorize the terminal output.
We still have to be careful about which terminals support certain 
features.

The same ANSI sequences will not work on Windows terminals, which
should be a long-term concern.
However, there is a package called colorama that will wrap stdout,
stripping ANSI color sequences and inserting the appropriate 
windows sequences.
