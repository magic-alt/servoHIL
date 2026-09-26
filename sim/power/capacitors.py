#!/usr/bin/env python3
"""Exact-catalog MLCC screening and integrity-checked reference curve import.

Hash matching proves byte identity, NOT manufacturer authenticity, lifetime
qualification or simultaneous bias/temperature bounds. Hardware stays blocked.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[2]


def load(name,root=ROOT):
    spec=importlib.util.spec_from_file_location('edv_caps_'+name,root/'sim/power'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def native_components(root=ROOT):
    spec=importlib.util.spec_from_file_location('edv_caps_sexpr',root/'tools/kicad_sexpr.py')
    sx=importlib.util.module_from_spec(spec);spec.loader.exec_module(sx)
    result={}
    for path in sorted((root/load('analysis',root).NATIVE).glob('*.kicad_sch')):
        for symbol in sx.items(sx.parse(path.read_text(encoding='utf-8')),'symbol'):
            props={p[1]:p[2] for p in sx.items(symbol,'property')}
            ref=props.get('Reference','')
            if ref.startswith('C'):
                if ref in result:raise ValueError('duplicate capacitor '+ref)
                result[ref]=props
    return result


def load_curve(path,part_number):
    """Load numbers from hashed CSV; retain original + normalization provenance."""
    path=Path(path).resolve();blob=path.read_bytes()
    try:
        m=json.loads(blob)
        if m['schema']!=1 or m['part_number']!=part_number:
            raise ValueError('curve schema/MPN mismatch')
        u=urlparse(m['source_url'])
        if u.scheme!='https' or not u.hostname:raise ValueError('HTTPS source required')
        date.fromisoformat(m['retrieved_on'])
        for key in ['reviewer','normalization_note']:
            if not isinstance(m[key],str) or not m[key].strip():raise ValueError('missing '+key)
        conditions=m['conditions']
        for key in ['temperature_c','ac_voltage_rms_v','frequency_hz']:
            if type(conditions[key]) not in (int,float) or not math.isfinite(conditions[key]):
                raise ValueError('invalid curve condition '+key)
        if conditions['temperature_c']<=-273.15 or min(conditions['ac_voltage_rms_v'],conditions['frequency_hz'])<=0:
            raise ValueError('unphysical curve conditions')
        contents={}
        for key in ['original','normalized_csv']:
            record=m[key];name=Path(record['file'])
            target=(path.parent/name).resolve()
            if name.is_absolute() or not target.is_relative_to(path.parent):
                raise ValueError('curve file escapes evidence pack')
            raw=target.read_bytes()
            if not re.fullmatch(r'[0-9a-f]{64}',record['sha256']) or hashlib.sha256(raw).hexdigest()!=record['sha256']:
                raise ValueError('curve file hash mismatch: '+key)
            contents[key]=raw
        reader=csv.reader(io.StringIO(contents['normalized_csv'].decode('utf-8-sig')))
        if next(reader,None)!=['voltage_v','retention']:raise ValueError('wrong curve CSV columns')
        points=[]
        for row in reader:
            if len(row)!=2:raise ValueError('wrong curve CSV row')
            points.append([float(row[0]),float(row[1])])
        curve={'part_number':part_number,'points':points}
        if not points or points[0][0]!=0 or not math.isclose(points[0][1],1,abs_tol=1e-9):
            raise ValueError('curve must be normalized to unity at zero DC bias')
        # Validates every row, finite data and strictly increasing voltage.
        load('qualification').curve_retention(curve,0,part_number)
        curve['provenance']={k:m[k] for k in ['source_url','retrieved_on','reviewer',
                                  'normalization_note','conditions','original','normalized_csv']}
        curve['provenance']['manifest_sha256']=hashlib.sha256(blob).hexdigest()
        curve['provenance']['evidence_class']='REFERENCE_CURVE_NOT_GUARANTEED_BOUND'
        return curve
    except (KeyError,TypeError,UnicodeError,csv.Error) as exc:
        raise ValueError('invalid curve evidence schema: '+str(exc)) from exc


def report(root=ROOT,curve_dir=None):
    a=load('analysis',root);q=load('qualification',root);base=a.build_report(root)
    native=native_components(root)
    catalog=json.loads((root/'sim/power/capacitor_candidates.json').read_text())
    reserve=catalog['bias_reserve_v'];a.positive(reserve)
    bias={'input_protected':max(base['assumptions']['vin_prot_v']),
          'cuk_transfer':base['cuk']['max_transfer_v'],
          'cuk_output':base['cuk']['magnitude_limits_v'][1]}
    for name,rail in [('buck_6v2','6V2_PRE'),('buck_3v3','3V3_D'),('buck_1v8','1V8_D')]:
        bias[name]=base['bucks'][rail]['static_limits_v'][1]
    for name,rail in [('ldo_5v0','+5V0_DAC'),('ldo_5v2','+5V2_PVDD'),('ldo_n5v2','-5V2_PVSS')]:
        bias[name]=base['ldos'][rail]['magnitude_limits_v'][1]
    if set(catalog['bank_candidates'])!=set(base['mlcc']):raise ValueError('candidate bank coverage mismatch')
    curves={};rows=[]
    for name,bank in base['mlcc'].items():
        mpn=catalog['bank_candidates'][name]
        row=dict(bank,bank=name,part_number=mpn,qualification='NOT_QUALIFIED',
                 bias_screen_v=bias[name]+reserve,curve_provenance=None)
        if mpn is None:
            row.update(status='BLOCKED_MPN');rows.append(row);continue
        p=catalog['parts'][mpn]
        for ref in bank['references']:
            item=native[ref];rating=re.search(r'/\s*(\d+(?:\.\d+)?)V\b',item['Value'])
            if not math.isclose(a.numeric(item['Value']),p['capacitance_f'],rel_tol=1e-9):
                raise ValueError(ref+': candidate capacitance no longer matches native')
            if item.get('Footprint')!=p['footprint'] or p['dielectric'] not in item['Value']:
                raise ValueError(ref+': candidate footprint/dielectric mismatch')
            if rating is None or p['rated_voltage_v']<float(rating[1]):
                raise ValueError(ref+': candidate voltage rating below native requirement')
        row.update({k:p[k] for k in ['source_url','rated_voltage_v','tolerance_loss','temperature_loss',
                                      'lifecycle','height_max_mm','note']})
        row['automotive_qualification']=p.get('automotive_qualification')
        if curve_dir is not None and mpn not in curves:
            path=Path(curve_dir)/(mpn+'.json')
            if path.is_file():curves[mpn]=load_curve(path,mpn)
        curve=curves.get(mpn);retention=None
        if curve is not None:
            # No extrapolation beyond archived curve voltage range.
            retention=q.curve_retention(curve,row['bias_screen_v'],mpn)
            row['curve_provenance']=curve['provenance']
        target=bank['target_f']
        row['aging_loss_sensitivity']=base['assumptions']['mlcc']['aging_loss']
        if target is None:
            row.update(status='BLOCKED_EFFECTIVE_C_TARGET',effective_f=None)
        else:
            row.update(a.mlcc_screen(bank['nominal_total_f'],1,p['tolerance_loss'],
                       p['temperature_loss'],row['aging_loss_sensitivity'],target,retention))
            row['status']=('BLOCKED_MISSING_CURVE' if curve is None else
                           'SCREEN_ONLY_REFERENCE_CURVE' if row['effective_f']>=target else 'FAIL_REFERENCE_CURVE_SCREEN')
        if row['bias_screen_v']>=p['rated_voltage_v']:row['status']='FAIL_VOLTAGE_RATING_SCREEN'
        rows.append(row)
    return {'status':'NOT_QUALIFIED','layout_allowed':False,'source_digest':a.content_digest(root),
            'catalog_checked_on':catalog['checked_on'],'imported_curve_count':len(curves),'banks':rows,
            'warning':'Curve byte integrity is not manufacturer authentication or full-temperature/lifetime validation. '
                      'Dynamic voltage reserve and aging remain assumptions; NRND/height/ESR/RMS-current require review.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/edv/capacitors')
    p.add_argument('--curve-dir',type=Path)
    args=p.parse_args()
    try:
        r=report(ROOT,args.curve_dir)
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/'capacitors.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
        print('MLCC banks:',len(r['banks']),'; imported reference curves:',r['imported_curve_count'],'; NOT_QUALIFIED')
    except (OSError,ValueError,KeyError) as exc:
        print('MLCC EVIDENCE ERROR:',exc,file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
