#!/usr/bin/env python3
"""Manufacturer candidate screening; never changes BOM, schematic or release gates."""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def analysis(root):
    spec=importlib.util.spec_from_file_location('edv_selection_analysis',root/'sim/power/analysis.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def copper_loss(rms_a,dcr_25c,temperature_c):
    if not all(map(math.isfinite,(rms_a,dcr_25c,temperature_c))) or rms_a<0 or dcr_25c<=0 or temperature_c<-100:
        raise ValueError('invalid copper loss input')
    return rms_a**2*dcr_25c*(1+.00393*(temperature_c-25))


def curve_retention(curve,voltage,part_number):
    """Interpolate a normalized DC-bias curve. Numerical helper, not evidence approval."""
    if curve is None:return 'BLOCKED_MISSING_CURVE'
    if curve.get('part_number')!=part_number:raise ValueError('curve MPN mismatch')
    if not math.isfinite(voltage) or voltage<0:raise ValueError('invalid voltage')
    points=curve.get('points',[])
    if len(points)<2:raise ValueError('missing curve points')
    last=-1
    for v,r in points:
        if not all(map(math.isfinite,(v,r))) or v<=last or not 0<r<=1:
            raise ValueError('invalid/nonmonotonic voltage curve')
        last=v
    if not points[0][0]<=voltage<=points[-1][0]:raise ValueError('no curve extrapolation')
    for (v0,r0),(v1,r1) in zip(points,points[1:]):
        if v0<=voltage<=v1:return r0+(r1-r0)*(voltage-v0)/(v1-v0)
    raise ValueError('voltage not covered')


def report(root=ROOT):
    a=analysis(root);values=a.native_values(root);base=a.build_report(root)
    data=json.loads((root/'sim/power/component_candidates.json').read_text())
    val=lambda r:a.numeric(values[r])
    rows=[]
    for ref,mpn in data['assignments'].items():
        part=data['parts'][mpn]
        if not math.isclose(part['inductance_h'],val(ref),rel_tol=1e-9):
            raise ValueError(f'{ref}: candidate inductance no longer matches native value')
        if ref in ['L201','L202','L203']:
            rail={'L201':'6V2_PRE','L202':'3V3_D','L203':'1V8_D'}[ref]
            stress=base['bucks'][rail]
            peak=stress['worst_peak']['peak_a'];rms=stress['worst_rms_a']
        else:
            stress=base['cuk'];side='lin' if ref=='L301' else 'lout'
            # CCM arithmetic only: invalid-mode corners cannot provide safe bounds.
            peak=stress['worst_switch']['switch_peak_a'];rms=stress['worst_'+side+'_rms_a']
        rows.append({'reference':ref,'part_number':mpn,'source_url':part['source_url'],
            'inductance_h':val(ref),'dcr_max_ohm_25c':part['dcr_max_ohm_25c'],
            'screen_peak_a':peak,'screen_rms_a':rms,
            'stress_model_status':stress['status'],
            'catalog_isat_to_peak_ratio':part['isat_typ_a_30pct_25c']/peak,
            'catalog_irms20_to_screen_ratio':part['irms_ref_a_20c_rise']/rms,
            'copper_loss_w_at125c':copper_loss(rms,part['dcr_max_ohm_25c'],125),
            'qualification':'NOT_QUALIFIED',
            'required_evidence':['L_I_T_CURVE','AC_CORE_AND_WINDING_LOSS','STARTUP_SHORT_CURRENT','BOARD_TEMPERATURE_RISE'],
            'open':'L(I,T), AC/core loss, startup/short circuit, footprint and board heat',
            'ratings_basis':'25C catalog typical/reference, NOT guaranteed actual-board current limits'})
    mlcc=[dict(bank=name,**row) for name,row in base['mlcc'].items()]
    return {'status':'SCREENED_NOT_QUALIFIED','layout_allowed':False,'source_digest':a.content_digest(root),
            'magnetics':rows,'mlcc':mlcc,'thermal':base['thermal'],
            'thermal_summary':base['thermal_summary'],'analytical_blocker_ids':base['blocker_ids'],
            'mlcc_curve_warning':'No vendor DC-bias curve imported. Interpolation helper is not a qualification certificate.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/edv/components')
    args=p.parse_args()
    r=report(ROOT);args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'selection.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    lines=['# Rev.B component screening — not purchase/layout approval','',
        '| Ref | Candidate | Peak A | RMS A | Isat/peak (25C catalog) | DC copper loss at 125C W |',
        '|---|---|---:|---:|---:|---:|']
    for x in r['magnetics']:
        lines.append(f"| {x['reference']} | {x['part_number']} | {x['screen_peak_a']:.4f} | {x['screen_rms_a']:.4f} | {x['catalog_isat_to_peak_ratio']:.2f} | {x['copper_loss_w_at125c']:.5f} |")
    lines+=['','## MLCC evidence gaps','', '| Bank | Nominal uF | Required uF | Minimum DC-bias retention | Status |','|---|---:|---:|---:|---|']
    for x in r['mlcc']:
        target='OPEN' if x.get('target_f') is None else f"{x['target_f']*1e6:.2f}"
        retain='OPEN' if x.get('required_bias_retention') is None else f"{x['required_bias_retention']:.3%}"
        lines.append(f"| {x['bank']} | {x['nominal_total_f']*1e6:.2f} | {target} | {retain} | {x['status']} |")
    lines+=['','## Thermal sensitivity','', 'Loss includes LDO input ground current. Buck total loss is conservatively assigned to the IC.','',
            '| Device | Largest screened Tj C | Condition |','|---|---:|---|']
    for device in sorted({t['device'] for t in r['thermal']}):
        worst=max((t for t in r['thermal'] if t['device']==device),key=lambda t:t['tj_screen_c'])
        lines.append(f"| {device} | {worst['tj_screen_c']:.2f} | ambient={worst['ambient_c']}C, Rtheta={worst['theta_c_per_w']}C/W; assumption, not bench result |")
    lines+=['','Do not freeze capacitor MPNs without voltage, temperature, aging and curve-source evidence.','No thermal, magnetic or capacitor qualification gate is changed.']
    (args.output/'selection.md').write_text('\n'.join(lines)+'\n')
    print('Component candidates:',len(r['magnetics']),'; MLCC banks:',len(r['mlcc']),'; qualification: BLOCKED')


if __name__=='__main__':main()
