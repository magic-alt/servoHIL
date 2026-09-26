"""Catalog-specific tolerance and byte-bound curve evidence, never board PASS."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_edv_qualification import module, ROOT

MPN='C3225X7R1C226M250AC'


def synthetic_pack(root):
    # Deliberately synthetic, NOT TDK or any manufacturer's measured curve.
    raw=b'SYNTHETIC TEST ONLY: 0 V = 1; 16 V = 0.5\n'
    csv=b'voltage_v,retention\n0,1\n16,0.5\n'
    (root/'synthetic-original.txt').write_bytes(raw)
    (root/'synthetic.csv').write_bytes(csv)
    data={'schema':1,'part_number':MPN,'source_url':'https://example.invalid/SYNTHETIC',
          'retrieved_on':'2026-09-24','reviewer':'SYNTHETIC TEST',
          'normalization_note':'Synthetic fixture; not engineering evidence.',
          'conditions':{'temperature_c':25,'ac_voltage_rms_v':.5,'frequency_hz':1000},
          'original':{'file':'synthetic-original.txt','sha256':hashlib.sha256(raw).hexdigest()},
          'normalized_csv':{'file':'synthetic.csv','sha256':hashlib.sha256(csv).hexdigest()}}
    path=root/(MPN+'.json');path.write_text(json.dumps(data))
    return path,data


class CapacitorEvidence(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'sim/power/capacitors.py').is_file(),
                        'missing catalog-specific capacitor screening and curve importer')
        self.m=module('capacitors')

    def test_current_22u_part_uses_20_percent_not_generic_10_percent(self):
        r=self.m.report(ROOT)
        row=next(x for x in r['banks'] if x['bank']=='buck_6v2')
        self.assertEqual(row['part_number'],MPN)
        self.assertEqual(row['tolerance_loss'],.20)
        self.assertAlmostEqual(row['required_bias_retention'],20/(44*.8*.85*.97))
        self.assertEqual(row['status'],'BLOCKED_MISSING_CURVE')
        self.assertFalse(r['layout_allowed'])
        self.assertEqual(r['imported_curve_count'],0)
        self.assertEqual(len(r['banks']),9)

    def test_lifecycle_and_unknown_input_mpn_are_not_silent_approval(self):
        rows={x['bank']:x for x in self.m.report(ROOT)['banks']}
        self.assertEqual(rows['input_protected']['status'],'BLOCKED_MPN')
        self.assertEqual(rows['cuk_transfer']['part_number'],'CGA6L2X7R1H105K160AA')
        self.assertEqual(rows['cuk_transfer']['lifecycle'],'PRODUCTION')
        self.assertEqual(rows['cuk_transfer']['automotive_qualification'],'AEC-Q200')
        self.assertEqual(rows['cuk_output']['rated_voltage_v'],25)
        self.assertIsNone(rows['cuk_output']['target_f'])
        self.assertTrue(all(x['qualification']=='NOT_QUALIFIED' for x in rows.values()))

    def test_no_assigned_bank_uses_nrnd_candidate(self):
        catalog=json.loads((ROOT/'sim/power/capacitor_candidates.json').read_text())
        assigned={mpn for mpn in catalog['bank_candidates'].values() if mpn}
        self.assertTrue(assigned)
        self.assertTrue(all('NRND' not in catalog['parts'][mpn]['lifecycle'] for mpn in assigned))

    def test_second_capacitor_nominal_change_rejects_stale_candidate(self):
        original=self.m.native_components(ROOT)
        original['C214']['Value']='10uF / 16V X7R, 1210'
        with patch.object(self.m,'native_components',return_value=original):
            with self.assertRaisesRegex(ValueError,'C214'):
                self.m.report(ROOT)

    def test_native_footprint_change_rejects_stale_candidate(self):
        native=self.m.native_components(ROOT)
        native['C410']['Footprint']='Capacitor_SMD:C_0805_2012Metric'
        with patch.object(self.m,'native_components',return_value=native):
            with self.assertRaisesRegex(ValueError,'C410'):
                self.m.report(ROOT)

    def test_curve_values_come_from_hashed_csv_not_manifest_points(self):
        with tempfile.TemporaryDirectory() as t:
            path,data=synthetic_pack(Path(t))
            data['points']=[[0,1],[16,1]]  # Cannot override actual hashed data.
            path.write_text(json.dumps(data))
            curve=self.m.load_curve(path,MPN)
            self.assertEqual(curve['points'],[[0.,1.],[16.,.5]])
            self.assertEqual(curve['provenance']['manifest_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_conditions_and_wrong_mpn_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path,data=synthetic_pack(Path(t))
            with self.assertRaises(ValueError):self.m.load_curve(path,'WRONG')
            del data['conditions']['temperature_c'];path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):self.m.load_curve(path,MPN)

    def test_corrupted_original_or_csv_rejected(self):
        for filename in ['synthetic-original.txt','synthetic.csv']:
            with self.subTest(filename=filename),tempfile.TemporaryDirectory() as t:
                path,_=synthetic_pack(Path(t))
                (Path(t)/filename).write_text('CHANGED')
                with self.assertRaisesRegex(ValueError,'hash'):
                    self.m.load_curve(path,MPN)

    def test_curve_paths_cannot_escape_pack(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);pack=root/'pack';pack.mkdir()
            path,data=synthetic_pack(pack)
            outside=root/'outside.csv';outside.write_bytes((pack/'synthetic.csv').read_bytes())
            for filename in ['../outside.csv',str(outside)]:
                data['normalized_csv']['file']=filename;path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):self.m.load_curve(path,MPN)
            (pack/'escape.csv').symlink_to(outside)
            data['normalized_csv']['file']='escape.csv';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):self.m.load_curve(path,MPN)

    def test_nonfinite_unsorted_or_non_normalized_csv_rejected(self):
        for text in ['voltage_v,retention\n0,1\n16,nan\n',
                     'voltage_v,retention\n16,.5\n0,1\n',
                     'voltage_v,retention\n0,.8\n16,.5\n']:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as t:
                path,data=synthetic_pack(Path(t));raw=text.encode()
                (Path(t)/'synthetic.csv').write_bytes(raw)
                data['normalized_csv']['sha256']=hashlib.sha256(raw).hexdigest()
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):self.m.load_curve(path,MPN)

    def test_imported_reference_curve_still_cannot_qualify_hardware(self):
        with tempfile.TemporaryDirectory() as t:
            synthetic_pack(Path(t))
            r=self.m.report(ROOT,Path(t))
            row=next(x for x in r['banks'] if x['bank']=='buck_6v2')
            self.assertEqual(r['imported_curve_count'],1)
            self.assertEqual(row['status'],'SCREEN_ONLY_REFERENCE_CURVE')
            self.assertEqual(row['qualification'],'NOT_QUALIFIED')
            self.assertFalse(r['layout_allowed'])
            self.assertIn('temperature_c',row['curve_provenance']['conditions'])


if __name__=='__main__':unittest.main()
