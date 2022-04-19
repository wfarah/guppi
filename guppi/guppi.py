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

        # parse the header of the first block
        header = self._parse_header()

        self.npol      = header['NPOL']
        self.obsnchan  = header['OBSNCHAN']
        self.nbits     = header['NBITS']
        self.blocsize  = header['BLOCSIZE']
        try:
            self.nants = header['NANTS']
        except:
            self.nants = -1

        try:
            self.nbeams = header['NBEAMS']
        except:
            self.nbeams = -1

        if self.nbits not in [4,8,16]:
            raise NotImplementedError("Only 4,8 and 16-bit data are implemented")

        if self.nbits == 4:
            self.data_raw = np.zeros(self.blocsize, dtype=np.int8)
            self.data = np.zeros_like(self.data_raw, dtype=np.complex64)
        elif self.nbits == 8:
            self.data_raw = np.zeros(self.blocsize, dtype=np.int8)
            self.data = np.zeros(shape=self.data_raw.size//2, dtype=np.complex64)
        elif self.nbits == 16:
            import warnings
            warnings.warn("Interpretting 16-bit data as float16, and not int16!!")
            self.data_raw = np.zeros(self.blocsize//2, dtype=np.float16)
            self.data = np.zeros(shape=self.data_raw.size//2, dtype=np.complex64)

        if self.nbeams != -1:
            self.nchan_per_ant   = self.obsnchan//self.nbeams

        if self.nants != -1 and self.nbeams == -1:
            self.nchan_per_ant    = self.obsnchan//self.nants

        self.nsamps_per_block = int(self.blocsize /
                (2*self.npol * self.obsnchan * (self.nbits/8)))

        self._reset_file()


    def __del__(self):
        self.file.close()

    def _reset_file(self):
        # seek back to the start of the file
        self.file.seek(0)

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


    def _check_consistency(self, header):
        npol     = header['NPOL']
        obsnchan = header['OBSNCHAN']
        nbits    = header['NBITS']
        blocsize = header['BLOCSIZE']
        try:
            nants    = header['NANTS']
        except KeyError as e:
            nants = -1

        try:
            nbeams = header['NBEAMS']
        except KeyError as e:
            nbeams = -1

        if nbits not in [4, 8, 16]:
            raise NotImplementedError("Only 4,8 and 16-bit data are implemented")

        assert npol     == self.npol
        assert obsnchan == self.obsnchan
        assert nbits    == self.nbits
        assert blocsize == self.blocsize
        assert nants    == self.nants
        assert nbeams   == self.nbeams

        nsamps_per_block = int(blocsize / (2*npol * obsnchan * (nbits/8)))

        if (2 * npol * obsnchan * (nbits/8) * nsamps_per_block ) != blocsize:
            raise RuntimeError("Bad block geometry: 2*%i*%i*%f*%i != %i"\
                    %(npol, obsnchan, nbits/8, nsamps_per_block, blocsize))

        if self.nbeams != -1:
            nchan_per_beam = obsnchan // nbeams
            if (nchan_per_beam * nbeams) != obsnchan:
                raise RuntimeError("obsnchan does not equally divide across antennas: "\
                        "obsnchan: %i, nants: %i, nchan_per_ant: %i",
                        obsnchan, nants, nchan_per_ant)


        if self.nants != -1 and self.nbeams == -1:
            nchan_per_ant    = obsnchan//nants

            if (nchan_per_ant * nants) != obsnchan:
                raise RuntimeError("obsnchan does not equally divide across antennas: "\
                        "obsnchan: %i, nants: %i, nchan_per_ant: %i",
                        obsnchan, nants, nchan_per_ant)



    #@jit(nopython=True)
    def read_next_block(self, complex64=True):
        header = self._parse_header()
        if not header:
            return None, None

        self._check_consistency(header)

        if self.nbits == 4:
            self.data_raw[:] = np.fromfile(self.file, dtype=np.int8,
                    count=self.blocsize)
            # every 1 sample is a complex number (4bit + 4bit) = (8bit) => complex64
            self.data[:] = (self.data_raw >> 4) + 1j*(self.data_raw << 4 >> 4)

        elif self.nbits == 8:
            self.data_raw[:] = np.fromfile(self.file, dtype=np.int8,
                    count=self.blocsize)
            # every 2 samples is a complex number (8bit + 8bit) => complex64
            self.data[:] = self.data_raw.astype(np.float32).view(np.complex64)

        elif self.nbits == 16:
            self.data_raw[:] = np.fromfile(self.file, dtype=np.float16,
                    count=self.blocsize//2)
            # every 1 sample is a 16bit float
            self.data[:] = self.data_raw[::2] + 1j*self.data_raw[1::2]


        if self.nbeams != -1:
            self.data_reshaped = self.data.reshape(self.nbeams,
                    self.nchan_per_ant, self.nsamps_per_block, self.npol)

        if self.nants != -1 and self.nbeams == -1: # "multi-antenna" raw file
            self.data_reshaped = self.data.reshape(self.nants,
                    self.nchan_per_ant, self.nsamps_per_block, self.npol)
        else:
            self.data_reshaped = self.data.reshape(self.obsnchan,
                    self.nsamps_per_block, self.npol)

        if header['DIRECTIO']:
            remainder = self.blocsize % DIRECT_IO_SIZE
            to_seek = (DIRECT_IO_SIZE - remainder)%DIRECT_IO_SIZE
            if to_seek:
                _ = self.file.read(to_seek)

        return header, self.data_reshaped




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
