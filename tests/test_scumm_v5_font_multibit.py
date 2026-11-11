"""Original generated glyphs; no external source archive required."""
import random
import struct
import unittest
import zlib
from same.engines.scumm_v5.font import encode_charset, decode_charset, raster_glyph
from same.errors import ResourceError
from test_scumm_v5_font import _copyright_free_charset


def source_font(bpp, width, height, x, y, slots):
    data = bytearray(21+4+256*4)
    data[6:21] = bytes([255,0,178,7,8,9,10,11,12,13,14,15,16,254,1])
    data[21:25] = struct.pack('<BBH',bpp,height,256)
    struct.pack_into('<I', data,25+65*4,len(data)-21)
    data.extend(bytes([width,height,x&255,y&255]))
    bits=''.join(format(p, f'0{bpp}b') for p in slots)
    bits += '0'*(-len(bits)%8)
    data.extend(int(bits[i:i+8],2) for i in range(0,len(bits),8))
    struct.pack_into('<I',data,0,len(data)-15)
    return bytes(data)


class MultibitFontTests(unittest.TestCase):
    def test_v1_unchanged_and_multibit_opt_in(self):
        s=_copyright_free_charset()
        self.assertEqual(encode_charset(s,logical_id=0,source_id=1),
                         encode_charset(s,logical_id=0,source_id=1,version=1,font_height=8,baseline=7,line_spacing=8))
        with self.assertRaises(ResourceError):
            encode_charset(source_font(2,1,1,0,0,[2]),logical_id=1,source_id=2)

    def test_independent_bit_packing_and_signed_metrics(self):
        rng=random.Random(91241)
        for bpp in (1,2,4):
            for _ in range(100):
                w,h=rng.randint(1,64),rng.randint(1,64)
                x,y=rng.randint(-128,127),rng.randint(-128,127)
                slots=bytes(rng.randrange(1<<bpp) for _ in range(w*h))
                s=source_font(bpp,w,h,x,y,slots)
                f=decode_charset(encode_charset(s,logical_id=4,source_id=2,version=2))
                g=f.glyphs[65]
                self.assertEqual((g.pixels,g.advance,g.x_origin,g.y_origin),(slots,w+x,x,y))
                self.assertEqual((f.font_height,f.line_spacing,f.bits_per_pixel),(h,h,bpp))
                self.assertEqual(f.color_map,bytes([0])+s[6:21])

    def test_opaque_zero_and_full_palette_and_signed_clip(self):
        f=decode_charset(encode_charset(source_font(2,3,2,-1,-1,[1,2,3,0,1,2]),logical_id=2,source_id=2,version=2))
        pixels,mask=raster_glyph(f,65,ink=240,x=1,y=1,width=3,height=2)
        self.assertEqual(pixels,bytes([240,0,178,0,240,0]))
        self.assertEqual(mask,bytes([1,1,1,0,1,1]))
        pixels,mask=raster_glyph(f,65,ink=240,x=0,y=0,width=2,height=1)
        self.assertEqual(pixels,bytes([240,0]));self.assertEqual(mask,b'\1\1')
        with self.assertRaises(ResourceError):raster_glyph(f,66,ink=1,x=0,y=0,width=2,height=1)

    def test_crc_and_crc_valid_invalid_directory(self):
        raw=encode_charset(source_font(4,3,1,0,0,[1,2,15]),logical_id=2,source_id=2,version=2)
        for i in (7,70,len(raw)-5,len(raw)-1):
            b=bytearray(raw);b[i]^=1
            with self.assertRaises(ResourceError):decode_charset(b)
        from same.engines.scumm_v5.font import _HEADER,_GLYPH2
        for offset,value in [(0,2),(1,99),(7,0)]:
            b=bytearray(raw);at=_HEADER.size+16+65*_GLYPH2.size
            b[at+offset]=value
            struct.pack_into('<I',b,len(b)-4,zlib.crc32(b[:-4]))
            with self.assertRaises(ResourceError):decode_charset(b)
        b=bytearray(raw);b[-5]|=1
        struct.pack_into('<I',b,len(b)-4,zlib.crc32(b[:-4]))
        with self.assertRaises(ResourceError):decode_charset(b)

if __name__=='__main__':unittest.main()
