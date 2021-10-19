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
    def _parse_header(self, return_raw=False):
        header = {}
        nbytes_read = 0
        hread = self.file.read(HEADER_KEY_VAL_SIZE).decode('UTF-8')
        #print(hread)
        if not hread: # we have reachec the end of file
            if return_raw:
                return None, None
            return None
        if return_raw:
            raw_header = ""
        nbytes_read += HEADER_KEY_VAL_SIZE
        while not hread.startswith("END"):
            if return_raw:
                raw_header += hread
            key, val = hread.split("=", 1)
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
        if return_raw:
            raw_header += hread
        if header['DIRECTIO']:
            remainder = nbytes_read % DIRECT_IO_SIZE
            to_seek = (DIRECT_IO_SIZE - remainder)%DIRECT_IO_SIZE
            tmp_direct_io = self.file.read(to_seek).decode('UTF-8')
            if return_raw:
                raw_header += tmp_direct_io
            nbytes_read += to_seek
        header['HEADER_SIZE'] = nbytes_read
        if return_raw:
            return raw_header, header
        return header

    #@jit(nopython=True)
    def read_next_block(self, complex64=True):
        header = self._parse_header()
        if not header:
            return None, None

        npol     = header['NPOL']
        obsnchan = header['OBSNCHAN']
        nbits    = header['NBITS']
        blocsize = header['BLOCSIZE']
        try:
            nants    = header['NANTS']
        except KeyError as e:
            nants = -1

        if nbits not in [4, 8]:
            raise NotImplementedError("Only 4 and 8-bit data are implemented")

        data_raw = np.fromfile(self.file, dtype=np.int8, count=blocsize)
        data = np.zeros_like(data_raw, dtype=np.complex64)

        if nbits == 4:
            data[:] = (data_raw >> 4) + 1j*(data_raw << 4 >> 4)

        elif nbits == 8:
            data = data_raw[::2] + 1j*data_raw[1::2]

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




    def _read_next_block_4bit_to_8bit(self):
        raw_header, header = self._parse_header(True)
        if not header:
            return None, None, None

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
        data = np.zeros(len(data_raw)*2, dtype=np.int8)
        data[::2]  = (data_raw >> 4) 
        data[1::2] = (data_raw << 4 >> 4)

        nsamps_per_block = int(blocsize / (2*npol * obsnchan * (nbits/8)))

        if (2 * npol * obsnchan * (nbits/8) * nsamps_per_block ) != blocsize:
            raise RuntimeError("Bad block geometry: 2*%i*%i*%f*%i != %i"\
                    %(npol, obsnchan, nbits/8, nsamps_per_block, blocsize))

        return raw_header, header, data



def convert_4bit_to_8bit(fname, outfile):
    ofile = open(outfile, "wb")

    g = Guppi(fname)
    raw_header, header, data = g._read_next_block_4bit_to_8bit()

    while raw_header:
        new_header = raw_header

        nbit_ind = raw_header.find("NBITS")
        orig = new_header[nbit_ind : nbit_ind + HEADER_KEY_VAL_SIZE]
        edited = orig.replace(" 4 ", " 8 ")
        new_header = new_header.replace(orig, edited)

        blocsize_ind = raw_header.find("BLOCSIZE")
        orig = raw_header[blocsize_ind : blocsize_ind + HEADER_KEY_VAL_SIZE]
        orig_ent = "  %i  " %(header['BLOCSIZE'])
        new_ent = ("  %i  " %(header['BLOCSIZE']*2))[:len(orig_ent)]
        edited = orig.replace(orig_ent, new_ent)
        new_header = new_header.replace(orig, edited)

        #nbit_entry = raw_header[nbit_ind : nbit_ind + HEADER_KEY_VAL_SIZE].replace(" 4 ", " 8 ")

        #new_header = raw_header[:nbit_ind]
        #new_header += nbit_entry
        #new_header += raw_header[nbit_ind+HEADER_KEY_VAL_SIZE:]

        ofile.write(new_header.encode("UTF-8"))
        data.tofile(ofile)

        raw_header, header, data = g._read_next_block_4bit_to_8bit()

    ofile.close()
