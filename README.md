# Guppi

guppi package for simple multi-antenna parsing of GUPPI RAW files

## Example:

```
from guppi import guppi
gfile = guppi.Guppi("some_multi_ant_guppi_file.raw")
hdr, data = gfile.read_next_block() #data.shape = [Nchan, Ntime, Npol] # single beam
# hdr is a python dictionary with observation key/value pair parameters
```

The above will read a single block along with its header.



### If you want to run through all the file:

```
from guppi import guppi
fnames = ["...1.raw", "...2.raw"]

for fname in fnames:
    gfile = guppi.Guppi(fname)
    while True:
        hdr, data = gfile.read_next_block()
        if hdr == None: # we reached end of file
            break # break so that we can load the next file
        do_something_with_data(data)
```

## Installation:
git clone the library and then run a:

`pip install .` 
