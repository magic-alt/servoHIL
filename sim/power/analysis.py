#!/usr/bin/env python3
"""Read-only Rev.B electrical screening. Results are NOT hardware qualification."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
NATIVE = Path('hardware/kicad/revB/axu2cgb_expansion')


def positive(*values):
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('physical parameter must be finite and positive')


def fraction(value, *, one=False):
    if not math.isfinite(value) or not 0 <= value <= 1 or (not one and value == 1):
        raise ValueError('invalid fractional bound')


def numeric(text):
    """Parse the native leading value, not units/numbers later in its comment."""
    m = re.match(r'^\s*(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)([pnumkMµR]?)(?:[FHVΩ]|ohm)?(?=\s|/|$)', text)
    if not m:
        raise ValueError('unrecognized leading component value: ' + text)
    scale = {'':1, 'R':1, 'p':1e-12, 'n':1e-9, 'u':1e-6, 'µ':1e-6, 'm':1e-3, 'k':1e3, 'M':1e6}
    result = float(m[1]) * scale[m[2]]
    positive(result)
    return result


def native_values(root=ROOT):
    spec = importlib.util.spec_from_file_location('edv_sexpr', root / 'tools/kicad_sexpr.py')
    sx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sx)
    result = {}
    for path in sorted((root / NATIVE).glob('*.kicad_sch')):
        for symbol in sx.items(sx.parse(path.read_text(encoding='utf-8')), 'symbol'):
            props = {p[1]:p[2] for p in sx.items(symbol, 'property')}
            ref = props.get('Reference', '')
            if not ref or ref.startswith('#'):
                continue
            if ref in result:
                raise ValueError('duplicate native reference: ' + ref)
            result[ref] = props['Value']
    if not result:
        raise ValueError('no native schematic components')
    return result


def divider(vref, upper, lower):
    positive(vref, upper, lower)
    return vref * (1 + upper / lower)


def divider_limits(vref_min, vref_max, upper, lower, tolerance):
    fraction(tolerance)
    return (divider(vref_min, upper*(1-tolerance), lower*(1+tolerance)),
            divider(vref_max, upper*(1+tolerance), lower*(1-tolerance)))


def ldo_limits(rset, tolerance, imin, imax, offset):
    positive(rset, imin, imax)
    fraction(tolerance)
    if imax < imin or not math.isfinite(offset) or offset < 0:
        raise ValueError('invalid LDO bounds')
    return rset*(1-tolerance)*imin-offset, rset*(1+tolerance)*imax+offset


def buck_stress(vin, vout, inductance, frequency, load):
    positive(vin, vout, inductance, frequency)
    if not math.isfinite(load) or load < 0 or vout >= vin:
        raise ValueError('invalid buck operating point')
    duty = vout/vin
    ripple = vout*(1-duty)/(inductance*frequency)
    return {'duty':duty, 'ripple_a':ripple, 'peak_a':load+ripple/2,
            'valley_a':load-ripple/2, 'rms_a':math.sqrt(load**2+ripple**2/12),
            'cin_rms_a':load*math.sqrt(duty*(1-duty)), 'ton_s':duty/frequency}


def cuk_stress(vin, magnitude, lin, lout, frequency, load, diode_drop, efficiency):
    positive(vin, magnitude, lin, lout, frequency, load, efficiency)
    fraction(efficiency, one=True)
    if not math.isfinite(diode_drop) or diode_drop < 0:
        raise ValueError('invalid diode voltage')
    duty = (magnitude+diode_drop)/(vin+magnitude+diode_drop)
    iin = magnitude*load/(vin*efficiency)
    di1 = vin*duty/(lin*frequency)
    di2 = vin*duty/(lout*frequency)
    return {'duty':duty, 'input_average_a':iin, 'output_average_a':load,
            'lin_ripple_a':di1, 'lout_ripple_a':di2,
            'lin_peak_a':iin+di1/2, 'lout_peak_a':load+di2/2,
            'lin_rms_a':math.sqrt(iin**2+di1**2/12),
            'lout_rms_a':math.sqrt(load**2+di2**2/12),
            'switch_peak_a':iin+load+(di1+di2)/2,
            'transfer_v':vin+magnitude+diode_drop,
            'transfer_rms_a_approx':math.sqrt(duty*load**2+(1-duty)*iin**2),
            'note':'CCM first-order sensitivity; output current is NOT switch current rating'}


def mlcc_screen(nominal, count, tolerance_loss, temperature_loss, aging_loss, target, bias_retention):
    positive(nominal, target)
    if type(count) is not int or count < 1:
        raise ValueError('invalid capacitor count')
    for loss in (tolerance_loss, temperature_loss, aging_loss):
        fraction(loss)
    unbiased = nominal*count*(1-tolerance_loss)*(1-temperature_loss)*(1-aging_loss)
    result = {'unbiased_derated_f':unbiased, 'required_bias_retention':target/unbiased,
              'effective_f':None, 'status':'BLOCKED_DC_BIAS_EVIDENCE'}
    if bias_retention is not None:
        fraction(bias_retention, one=True)
        result['effective_f'] = unbiased*bias_retention
        result['status'] = 'SCREEN_ONLY' if result['effective_f'] >= target else 'FAIL_ASSUMED_RETENTION'
    return result


def ldo_power(vin, vout, load, ground_current):
    positive(vin, vout)
    if vout >= vin or min(load, ground_current) < 0 or not all(map(math.isfinite,(load,ground_current))):
        raise ValueError('invalid LDO power inputs; use magnitudes for negative LDO')
    return (vin-vout)*load + vin*ground_current


def content_digest(root=ROOT):
    h = hashlib.sha256()
    paths = list((root/NATIVE).glob('*.kicad_sch')) + list((root/'sim').rglob('*'))
    for path in sorted(p for p in paths if p.is_file() and '__pycache__' not in str(p) and p.suffix != '.pyc'):
        h.update(str(path.relative_to(root)).encode()+b'\0'+path.read_bytes()+b'\0')
    return h.hexdigest()


def build_report(root=ROOT):
    values = native_values(root)
    a = json.loads((root/'sim/power/assumptions.json').read_text())
    def val(ref): return numeric(values[ref])
    for ref, part in [('U201','AP63201'),('U202','AP63201'),('U203','AP63201'),
                      ('U211','LT3045'),('U212','LT3045'),('U301','LT8330'),('U302','LT3094')]:
        if not values[ref].startswith(part):
            raise ValueError(f'{ref}: topology/model binding changed; review assumptions')
    report = {'scope':'ANALYTICAL_SCREENING', 'qualification':'BLOCKED', 'layout_allowed':False,
              'source_digest':content_digest(root), 'assumptions':a,
              'component_values':{}, 'bucks':{}, 'ldos':{}, 'thermal':[], 'blocker_ids':[]}
    b = a['buck'];tol = a['resistor_tolerance']
    for i, rail in enumerate(['6V2_PRE','3V3_D','1V8_D']):
        ur, lr, ind = f'R{210+i*10}', f'R{211+i*10}', f'L{201+i}'
        v = divider(.8,val(ur),val(lr))
        lo, hi = divider_limits(b['feedback_v'][0], b['feedback_v'][-1], val(ur),val(lr),tol)
        cases = []
        for vin, vo, freq, lf, load in itertools.product(a['vin_prot_v'],[lo,v,hi],b['frequency_hz'],b['inductor_fraction'],[0,b['load_budget_a'][rail]]):
            cases.append({'vin':vin,'vout':vo,'frequency':freq,'l_fraction':lf,'load':load,
                          **buck_stress(vin,vo,val(ind)*lf,freq,load)})
        worst = max(cases,key=lambda r:r['peak_a'])
        ripple = max(r['ripple_a'] for r in cases)
        report['bucks'][rail] = {'nominal_v':v, 'static_limits_v':[lo,hi], 'inductor_h':val(ind),
            'case_count':len(cases), 'worst_peak':worst, 'minimum_valley_a':min(r['valley_a'] for r in cases),
            'worst_rms_a':max(r['rms_a'] for r in cases),
            'ripple_v_screen':ripple/(8*min(b['frequency_hz'])*min(b['output_effective_cap_f']))+ripple*max(b['capacitor_esr_ohm']),
            'status':'SCREEN_ONLY_FREQUENCY_AND_ESR_NOT_GUARANTEED'}
        for eta, theta, ta in itertools.product(b['efficiency'],b['theta_ja_c_per_w'],a['ambient_c']):
            # Conservative upper envelope: attribute all converter loss to IC (includes inductor loss).
            loss = hi*b['load_budget_a'][rail]*(1/eta-1)
            report['thermal'].append({'device':f'U{201+i}', 'ambient_c':ta,'theta_c_per_w':theta,
                'efficiency_assumed':eta,'loss_upper_envelope_w':loss,'tj_screen_c':ta+theta*loss,
                'status':'SENSITIVITY_NOT_THERMAL_QUALIFICATION'})
    c = a['cuk'];mag = divider(.8,val('R410'),val('R411'))
    cuk_cases = [dict(vin=vin,frequency=freq,**cuk_stress(vin,mag,val('L301')*lf,val('L302')*lf,freq,c['output_load_a'],c['diode_drop_v'],c['efficiency']))
                 for vin,freq,lf in itertools.product(a['vin_prot_v'],c['frequency_hz'],b['inductor_fraction'])]
    report['cuk'] = {'nominal_v':-mag, 'worst_switch':max(cuk_cases,key=lambda r:r['switch_peak_a']),
                     'worst_lin_rms_a':max(r['lin_rms_a'] for r in cuk_cases),
                     'worst_lout_rms_a':max(r['lout_rms_a'] for r in cuk_cases),
                     'max_transfer_v':max(r['transfer_v'] for r in cuk_cases),
                     'note':'0.15A Cuk load includes allowance for LT3094 GND current; assumptions documented'}
    l = a['ldo']
    for ref, rset, rail, device, supply in [('U211','R240','+5V0_DAC','LT3045',report['bucks']['6V2_PRE']['static_limits_v'][1]),
                                           ('U212','R260','+5V2_PVDD','LT3045',report['bucks']['6V2_PRE']['static_limits_v'][1]),
                                           ('U302','R420','-5V2_PVSS','LT3094',mag*1.025)]:
        lo, hi = ldo_limits(val(rset),tol,min(l['set_current_a']),max(l['set_current_a']),l['offset_bound_v'])
        report['ldos'][rail] = {'nominal_magnitude_v':val(rset)*100e-6,'magnitude_limits_v':[lo,hi],
                               'ground_current_screen_a':l['gnd_current_screen_a'][device]}
        loss = ldo_power(supply,lo,l['load_budget_a'][rail],l['gnd_current_screen_a'][device])
        for ta,theta in itertools.product(a['ambient_c'],l['theta_ja_c_per_w']):
            report['thermal'].append({'device':ref,'ambient_c':ta,'theta_c_per_w':theta,
                                     'loss_w':loss,'tj_screen_c':ta+theta*loss,
                                     'status':'SENSITIVITY_INCLUDES_GND_CURRENT'})
    plus=report['ldos']['+5V2_PVDD']['magnitude_limits_v']
    minus=report['ldos']['-5V2_PVSS']['magnitude_limits_v']
    span=plus[1]+minus[1];d=a['dac']
    report['dac_supply']={'maximum_static_span_v':span,'maximum_negative_magnitude_v':minus[1],
        'span_limit_v':d['maximum_supply_span_v'],'pvss_minimum_v':d['minimum_pvss_v'],
        'static_span_margin_v':d['maximum_supply_span_v']-span,
        'minimum_headroom_v':min(plus[0],minus[0])-d['requested_output_peak_v'],
        'recommended_headroom_v':d['recommended_headroom_v'],
        'status':'FAIL_FULL_CONDITION' if span>d['maximum_supply_span_v'] or minus[1]>abs(d['minimum_pvss_v']) else 'SCREEN_ONLY'}
    if report['dac_supply']['status'].startswith('FAIL'):
        report['blocker_ids'].append('DAC_SUPPLY_FULL_CONDITION')
    if report['dac_supply']['minimum_headroom_v'] < d['recommended_headroom_v']:
        report['blocker_ids'].append('DAC_OUTPUT_HEADROOM')
    # Bounds for a symmetric +/-5V rail when retaining these LDOs: no simple RSET tweak solves both.
    report['rset_feasibility']={
        'minimum_ohm_for_headroom':(d['requested_output_peak_v']+d['recommended_headroom_v']+l['offset_bound_v'])/(min(l['set_current_a'])*(1-tol)),
        'maximum_ohm_for_pvss_limit':(abs(d['minimum_pvss_v'])-d['dynamic_margin_v']-l['offset_bound_v'])/(max(l['set_current_a'])*(1+tol)),
        'action':'Review tighter rail accuracy or allowed output span; do not blindly lower RSET'}
    m=a['mlcc']
    report['mlcc']={}
    for name,ref,count,target in [('buck_6v2','C213',2,20e-6),('ldo_5v0','C243',2,10e-6)]:
        if ref not in values:
            raise ValueError('native capacitor binding missing: '+ref)
        report['mlcc'][name]=dict(ref=ref,**mlcc_screen(val(ref),count,m['tolerance_loss'],m['temperature_loss'],m['aging_loss'],target,m['bias_retention']))
    report['blocker_ids'] += ['MLCC_DC_BIAS_CURVES','MAGNETICS_LOSS_AND_LAYOUT','SWITCHING_VENDOR_MODEL',
                             'INPUT_PROTECTION_ENERGY','PARTIAL_POWER_BACKFEED','BENCH_THERMAL_AND_TRANSIENT']
    for ref in sorted(values):
        if ref.startswith(('R','L','C','U')) and not ref.startswith('PWR'):
            report['component_values'][ref]=values[ref]
    # Source byte hash invalidates nominal calculations when the native schematic changes.
    report['native_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted((root/NATIVE).glob('*.kicad_sch'))}
    return report


def write_report(report, output):
    output.mkdir(parents=True,exist_ok=True)
    (output/'analytical.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    lines=['# Rev.B electrical screening — NOT hardware PASS','',
           'Qualification: **BLOCKED**; layout_allowed=false.',
           'Source digest: `'+report['source_digest']+'`','',
           '| Buck | Nominal V | Static min/max V | Worst peak A | Worst RMS A |',
           '|---|---:|---|---:|---:|']
    for rail,r in report['bucks'].items():
        lines.append(f"| {rail} | {r['nominal_v']:.6f} | {r['static_limits_v'][0]:.6f} / {r['static_limits_v'][1]:.6f} | {r['worst_peak']['peak_a']:.4f} | {r['worst_rms_a']:.4f} |")
    lines += ['', '## DAC supply full-condition finding', '', '```json',json.dumps(report['dac_supply'],indent=2),'```',
              '', '## Open blockers', '', '\n'.join('- '+b for b in report['blocker_ids']),
              '', 'All frequency/efficiency/thermal/aging sensitivities are named in assumptions.json. No vendor transient model or bench PASS inferred.']
    (output/'analytical.md').write_text('\n'.join(lines)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--output',type=Path,default=ROOT/'build/edv')
    p.add_argument('--strict-design',action='store_true')
    a=p.parse_args()
    try:
        r=build_report(a.root);write_report(r,a.output)
    except (ValueError,KeyError,FileNotFoundError) as exc:
        print('EDV INPUT ERROR:',exc,file=sys.stderr);return 1
    print(json.dumps({'qualification':r['qualification'],'blocker_ids':r['blocker_ids'],'dac_supply':r['dac_supply']},indent=2))
    return 2 if a.strict_design and r['blocker_ids'] else 0


if __name__=='__main__':raise SystemExit(main())
