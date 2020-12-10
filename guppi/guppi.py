import numpy as np
#from numba import jit

HEADER_KEY_VAL_SIZE = 80 #bytes
DIRECT_IO_SIZE      = 512

class Guppi():
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
        #print(hread)
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
        if header['DIRECTIO']:
            remainder = nbytes_read % DIRECT_IO_SIZE
            to_seek = (DIRECT_IO_SIZE - remainder)%DIRECT_IO_SIZE
            _ = self.file.read(to_seek)
            nbytes_read += to_seek
        header['HEADER_SIZE'] = nbytes_read
        return header

    #@jit(nopython=True)
    def read_next_block(self):
        header = self._parse_header()
        if not header:
            return None

        npol     = header['NPOL']
        obsnchan = header['OBSNCHAN']
        nbits    = header['NBITS']
        blocsize = header['BLOCSIZE']
        try:
            nants    = header['NANTS']
        except KeyError as e:
            nants = -1

        if nbits != 4:
            raise NotImplementedError("Only 4-bit data is implemented")

        data_raw = np.fromfile(self.file, dtype=np.int8, count=blocsize)
        data = np.zeros_like(data_raw, dtype=np.complex64)
        data[:] = (data_raw >> 4) + 1j*(data_raw << 4 >> 4)

        nsamps_per_block = int(blocsize / (2*npol * obsnchan * (nbits/8)))

        if (2 * npol * obsnchan * (nbits/8) * nsamps_per_block ) != blocsize:
            raise RuntimeError("Bad block geometry: 2*%i*%i*%f*%i != %i"\
                    %(npol, obsnchan, nbits/8, nsamps_per_block, blocsize))

        if nants != -1: # "multi-antenna" raw file
            nchan_per_ant    = obsnchan//nants

            if (nchan_per_ant * nants) != obsnchan:
                raise RuntimeError("obsnchan does not equally divide across antennas: "\
                        "obsnchan: %i, nants: %i, nchan_per_ant: %i",
                        obsnchan, nants, nchan_per_ant)

            data = data.reshape(nants, nchan_per_ant, nsamps_per_block, npol)
        else:
            data = data.reshape(obsnchan, nsamps_per_block, npol)

        if header['DIRECTIO']:
            remainder = blocsize % DIRECT_IO_SIZE
            to_seek = (DIRECT_IO_SIZE - remainder)%DIRECT_IO_SIZE
            if to_seek:
                _ = self.file.read(to_seek)

        return header, data


