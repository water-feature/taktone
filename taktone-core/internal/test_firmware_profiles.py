"""Base detection and wrong-version protection against supplied exact stocks."""
import json
import unittest
from types import SimpleNamespace
from convert import ROOT,syx,apply
from firmware_profiles import PROFILES,identify_base,profile_for,fingerprint_spans
from shutdown_patch import make_shutdown_patch


class BaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs=[(p,syx.Syx.load(ROOT.parent/'firmware'/p.filename)) for p in PROFILES]

    def test_both_stock_bases_detected(self):
        for p,s in self.refs:
            with self.subTest(version=p.version):
                detected,ref,evidence=identify_base(s,self.refs)
                self.assertEqual(detected,p)
                self.assertEqual(profile_for(s.section(3)),p)
                self.assertEqual(len(evidence['fingerprints']),4)

    def test_display_version_does_not_select_base(self):
        for p,s in self.refs:
            mod=SimpleNamespace(stored=s.stored,version='2.0a',section=s.section)
            self.assertEqual(identify_base(mod,self.refs)[0],p)

    def test_wrong_stock_and_forged_metadata_rejected(self):
        a,b=self.refs
        for p,s in self.refs:
            wrong=next(x for x in self.refs if x[0]!=p)
            with self.assertRaises(ValueError):identify_base(s,[wrong])
        # Substituting 1.54 metadata onto a 1.53 application must not pass.
        forged=SimpleNamespace(stored=b[1].stored,section=a[1].section)
        with self.assertRaises(ValueError):identify_base(forged,self.refs)

    def test_changed_native_dependency_rejected(self):
        for p,s in self.refs:
            image=bytearray(s.section(3));image[fingerprint_spans(p)[0][0]]^=1
            mod=SimpleNamespace(stored=s.stored,section=lambda sid:bytes(image))
            with self.assertRaises(ValueError):identify_base(mod,self.refs)

    def test_both_source_builds_match_pinned_recipes(self):
        dn=syx.Syx.load(ROOT.parent/'firmware/Digitone_and_Digitone_Keys_OS1.43.syx')
        for p,s in self.refs:
            name='patch-data-'+p.version+'.json'
            image,details=make_shutdown_patch(s.section(3))
            self.assertEqual(image,apply(json.loads((ROOT/name).read_text()),s,dn))
            self.assertEqual(details['base_version'],p.version)


if __name__=='__main__':
    unittest.main()
