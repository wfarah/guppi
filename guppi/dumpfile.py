import numpy as np
#from numba import jit

HEADER_KEY_VAL_SIZE = 80 #bytes
DIRECT_IO_SIZE      = 512

HPGUPPI_HDR_SIZE     = 5*80*512
HPGUPPI_DATA_SIZE    = 128*1024*1024
HPGUPPI_N_BLOCKS     = 24

class Dumpfile():
    """
    A very basic guppi raw file reader
    """
    def __init__(self, fname):
        if type(fname) != str:
            raise RuntimeError("Please provide string filename")
        self.fname = fname
        self.file  = open(fname, "rb")

    def __del__(self):
        self.file.close()

    #@jit(nopython=True)
    def _parse_header(self):
        header = {}
        nbytes_read = 0
        hread = self.file.read(HEADER_KEY_VAL_SIZE).decode('UTF-8')
        if not hread: # we have reachec the end of file
            return None
        nbytes_read += HEADER_KEY_VAL_SIZE
        while not hread.startswith("END"):
            key, val = hread.split("=")
            key = key.strip()
            val = val.strip()

            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                val = val.strip("'").strip()

            header[key] = val
            hread = self.file.read(HEADER_KEY_VAL_SIZE).decode('UTF-8')
            nbytes_read += HEADER_KEY_VAL_SIZE

        assert hread == "END"+" "*77, "Not a GUPPI RAW format"

        _ = self.file.read(HPGUPPI_HDR_SIZE - nbytes_read)
        nbytes_read += HPGUPPI_HDR_SIZE - nbytes_read

        if header['DIRECTIO']:
            remainder = nbytes_read % DIRECT_IO_SIZE
            to_seek = (DIRECT_IO_SIZE - remainder)%DIRECT_IO_SIZE
            _ = self.file.read(to_seek)
        return header

    def read_next_block(self):
        header = self._parse_header()
        if not header:
            return None

        blocsize = header['BLOCSIZE']
        nbits    = header['NBITS']
        try:
            nants    = header['NANTS']
        except KeyError as e:
            nants = -1

        if nbits != 4:
            raise NotImplementedError("Only 4-bit data is implemented")

        data_raw = np.fromfile(self.file, dtype=np.int8, count=blocsize)
        data = np.zeros_like(data_raw, dtype=np.complex64)
        data[:] = (data_raw >> 4) + 1j*(data_raw << 4 >> 4)
        self.file.seek(HPGUPPI_DATA_SIZE - blocsize, 1)

        return header, data
