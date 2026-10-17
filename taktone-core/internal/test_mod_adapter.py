"""Real stock core plus synthetic instances of the observed mod loader."""
import json
import struct
import unittest
from pathlib import Path
from mod_adapter import BASE, HOOK, STOCK_INIT, TEMPLATE, recognize, choose_ram, adapt
from convert import ROOT, syx, apply


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        version = getattr(cls, 'version', '1.53')
        dt = syx.Syx.load(ROOT.parent/'firmware'/('Digitakt_OS'+version+'.syx'))
        dn = syx.Syx.load(ROOT.parent/'firmware/Digitone_and_Digitone_Keys_OS1.43.syx')
        cls.stock = dt.section(3)
        recipe = 'patch-data-'+version+'.json'
        cls.core = apply(json.loads((ROOT/recipe).read_text()),dt,dn)

    def mod(self, dest=0x47BE0000, payload_bytes=64, clear_bytes=64):
        stub = bytearray(TEMPLATE)
        for off, value in [(2,BASE+len(self.stock)+96),(8,dest),(14,payload_bytes//4),(26,dest+payload_bytes),(32,clear_bytes//4)]:
            struct.pack_into('>I',stub,off,value)
        m = bytearray(self.stock + stub + bytes(range(payload_bytes)))
        struct.pack_into('>I', m, HOOK-BASE+2, BASE+len(self.stock))
        return m

    def test_relocates_core_preserves_mod_and_chains_startup(self):
        mod = self.mod()
        # An unrelated application edit must also survive.
        mod[0x100] ^= 1
        image, report = adapt(self.stock, bytes(mod), self.core)
        self.assertIsNotNone(image)
        self.assertGreaterEqual(report['core_ram']['start'],0x47BE0080)
        self.assertEqual(image[len(self.stock):len(mod)], mod[len(self.stock):])
        self.assertEqual(image[0x100],mod[0x100])
        core_at = report['core_stub']-BASE
        self.assertEqual(image[core_at:core_at+6],bytes.fromhex('2f002f082f09'))
        self.assertIn(bytes.fromhex('225f205f201f4ef9')+struct.pack('>I',BASE+len(self.stock)),image[core_at:core_at+44])
        self.assertEqual(struct.unpack_from('>I',image,HOOK-BASE+2)[0],report['core_stub'])
        self.assertEqual(struct.unpack_from('>I',image,core_at+8)[0],report['core_payload_source'])
        # Mod loader and its single stock-init tail jump are unchanged.
        self.assertEqual(report['startup_chain'],[report['core_stub'],BASE+len(self.stock),STOCK_INIT])
        self.assertEqual(image[len(self.stock):len(self.stock)+96],mod[len(self.stock):len(self.stock)+96])

    def test_lower_mod_ram_does_not_relocate_core(self):
        image, report = adapt(self.stock, bytes(self.mod(0x47BC0000)), self.core)
        self.assertEqual(report['core_ram']['start'],0x47BE0000)

    def test_template_instructions_and_bounds_fail_closed(self):
        for offset in (0,18,38,84,95):
            mod = self.mod();mod[len(self.stock)+offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                recognize(self.stock,mod)
        mod=self.mod()
        with self.assertRaises(ValueError):recognize(self.stock,mod[:-4])
        mod=self.mod();struct.pack_into('>I',mod,len(self.stock)+14,0)
        with self.assertRaises(ValueError):recognize(self.stock,mod)
        mod=self.mod();struct.pack_into('>I',mod,len(self.stock)+26,0x47BE0084)
        with self.assertRaises(ValueError):recognize(self.stock,mod)
        with self.assertRaises(ValueError):recognize(self.stock,self.mod(0x47000000))

    def test_stock_initializer_change_is_rejected(self):
        mod=self.mod();mod[STOCK_INIT-BASE]^=1
        with self.assertRaises(ValueError):recognize(self.stock,mod)

    def test_additional_core_conflict_rejected(self):
        mod=self.mod();mod[0x40000FC8-BASE]^=1
        image,report=adapt(self.stock,bytes(mod),self.core)
        self.assertIsNone(image)
        self.assertEqual(report['status'],'conflict')

    def test_declared_ram_drives_placement_and_exhaustion(self):
        image,report=adapt(self.stock,bytes(self.mod(0x47BC0000)),self.core,
                           [dict(start='0x47be0000',end='0x47bf0000')])
        self.assertEqual(report['core_ram']['start'],0x47BF0000)
        with self.assertRaises(ValueError):
            adapt(self.stock,bytes(self.mod()),self.core,[dict(start=0x47BE0000,end=0x47C00000)])
        with self.assertRaises(ValueError):
            choose_ram(0x1000,[(0x47BE0000,0x47BFF800)])

    def test_recipe_source_mismatch_rejected(self):
        with self.assertRaises(ValueError):adapt(self.stock,bytes(self.mod()),self.core+b'changed')


class Adapter154Tests(AdapterTests):
    version = '1.54'


if __name__ == '__main__':
    unittest.main()
