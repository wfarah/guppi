# Guppi

guppi package for simple multi-antenna parsing of GUPPI RAW files

## Example:

```
from guppi import guppi
gfile = guppi.Guppi("some_multi_ant_guppi_file.raw")
hdr, data = gfile.read_next_block() #data.shape = [Nants, Nchan, Ntime, Npol]
```

## Installation:
A `pip install .` after cloning the repository is sufficient to install the library
