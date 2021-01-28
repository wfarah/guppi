# Guppi

guppi package for simple multi-antenna parsing

## Example:

```
from guppi import guppi
gfile = guppi.Guppi("some_multi_ant_guppi_file.raw")
hdr, data = gfile.read_next_block() #data.shape = [Nants, Nchan, Ntime, Npol]
```
