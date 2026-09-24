#!/usr/bin/env python3
"""Portable ngspice/LTspice screening, explicitly NOT vendor macro-models.

Clean .cir decks contain portable directives; the ngspice .control wrapper is
separate. No proprietary vendor models are redistributed or claimed executed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
MEASURES=['output_mean','ripple_v','current_peak','startup_s','step_min','step_max','shutdown_v']


def analysis(root):
    spec=importlib.util.spec_from_file_location('edv_analysis_spice',root/'sim/power/analysis.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def parse_measures(log, requested):
    if re.search(r'(?im)^\s*(?:error\b|fatal\b)|measure.*failed|timestep too small|simulation interrupted',log):
        raise ValueError('SPICE reports an error/failed measurement')
    result={}
    for key in requested:
        rows=re.findall(r'(?im)^\s*'+re.escape(key)+r'\s*=\s*(\S+)',log)
        if len(rows)!=1:raise ValueError(f'measure {key}: expected once, found {len(rows)}')
        try:value=float(rows[0])
        except ValueError as exc:raise ValueError('invalid SPICE measure '+key) from exc
        if not math.isfinite(value):raise ValueError('nonfinite SPICE measure '+key)
        result[key]=value
    return result


def measures(nominal, step, release, settled, end):
    # ngspice FIND at exact TSTOP can fail on floating point endpoint rounding.
    return f'''
.meas tran output_mean AVG v(mag) FROM={settled[0]} TO={settled[1]}
.meas tran ripple_v PP v(mag) FROM={settled[0]} TO={settled[1]}
.meas tran current_peak MAX v(ipk) FROM=0 TO={end*0.999}
.meas tran startup_s WHEN v(mag)={0.9*nominal} RISE=1
.meas tran step_min MIN v(mag) FROM={step} TO={release}
.meas tran step_max MAX v(mag) FROM={release} TO={settled[1]}
.meas tran shutdown_v FIND v(mag) AT={end*0.999}
'''


def switching_deck(kind,vin,vo,load,l1,l2,cap,derated,transfer=1e-6):
    """Actual power network, imposed fixed duty and input ramp, NOT chip soft-start."""
    if kind=='buck':
        freq=450000 if derated else 500000
        ramp=.004;step=.007;release=.010;off=.012;end=.018
        settle=(.011,.0119);duty=vo/vin
        network=f'''
.model HS SW(Ron=0.125 Roff=1e9 Vt=0.5 Vh=0.02)
.model LS SW(Ron=0.068 Roff=1e9 Vt=0.5 Vh=0.02)
.model BODY D(Is=1n Rs=0.05 N=1.5)
Shigh vin sw gate 0 HS
Blow glow 0 V=(1-V(gate))*(V(enable)>0.5)
Slow sw 0 glow 0 LS
Dhigh sw vin BODY
Dlow 0 sw BODY
Rldcr sw lind 0.1
Loutput lind out {l1}
Bmag mag 0 V=v(out)
Bpk ipk 0 V=abs(i(Loutput))
'''
    elif kind=='cuk':
        freq=1800000 if derated else 2000000
        ramp=.0004;step=.0009;release=.0015;off=.0022;end=.003
        settle=(.0019,.0021);duty=(vo+.5)/(vin+vo+.5)
        network=f'''
.model SWMOD SW(Ron=0.3 Roff=1e9 Vt=0.5 Vh=0.02)
.model SCHOTTKY D(Is=1u Rs=0.08 N=1.1)
Rinput vin li1 0.1
Linput li1 sw {l1}
Vsense sw swsense 0
Smain swsense 0 gate 0 SWMOD
Ctransfer sw xcap {transfer}
Rtransfer xcap negx 0.03
Dfly negx 0 SCHOTTKY
Routput negx li2 0.1
Loutput li2 out {l2}
Bmag mag 0 V=-v(out)
Bpk ipk 0 V=abs(i(Vsense))
'''
    else:raise ValueError('unknown switching topology')
    dt=1/(freq*30)
    return f'''EDV {kind} SWITCHED POWER STAGE - NOT A VENDOR MODEL
* Open-loop fixed duty with an INPUT VOLTAGE RAMP; this is NOT IC soft-start behavior.
* Explicit PULSE edges give the solver breakpoints; no untracked comparator crossing.
* DOES NOT verify compensation, soft start, current limit, hiccup or protection.
* Ron/ESR/DCR/diode are assumptions; native capacitor totals are nominal, NOT effective.
Vbus vin 0 PWL(0 0 {ramp} {vin} {end} {vin})
Venable enable 0 PWL(0 1 {off} 1 {off+1e-6} 0 {end} 0)
Vpwm pwm 0 PULSE(0 1 0 1n 1n {duty/freq-1e-9} {1/freq})
Bdrive gate 0 V=v(pwm)*(v(enable)>0.5)
Vstep loadstep 0 PWL(0 0 {step} 0 {step+2e-6} 1 {release} 1 {release+2e-6} 0 {end} 0)
{network}
Bload out 0 I=v(out)*({0.5*load/vo}+{0.5*load/vo}*v(loadstep))
Resr out cout 0.02
Cout cout 0 {cap}
Rbleed out 0 2200
.options reltol=0.001 abstol=1n vntol=1u method=gear
.save v(mag) v(out) v(ipk) v(vin) v(gate)
.tran {dt*5} {end} 0 {dt}
{measures(vo,step,release,settle,end)}
.meas tran gate_duty AVG v(gate) FROM={settle[0]} TO={settle[1]}
.end
'''


def ldo_deck(vin,vo,load,rset,cset,iset,limit,negative=False,cout=20e-6):
    """Magnitude envelope only; negative case is NOT an LT3094 macro-model."""
    return f'''EDV LDO ENVELOPE - NOT A VENDOR MODEL
* RSET/CSET are native values. gm=20A/V, fast-start=1.8mA and 0.45V dropout assumed.
* No validation of loop stability/PSRR/noise/thermal/reverse-current/PG behavior.
* negative={negative}; out_physical is sign-restored probe, not actual negative silicon.
Vbus vin 0 PWL(0 0 5m {vin} 80m {vin} 80.1m 0 100m 0)
Biset 0 set I=(v(vin)>2)*({iset}+(v(set)<{vo*.95})*0.0018)
Rset set 0 {rset}
Cset set 0 {cset}
Bpass vin out I=max(0,min({limit},20*(min(v(set),max(v(vin)-0.45,0))-v(out))))
Ignd vin 0 0.003
Resr out cap 0.02
Cout cap 0 {cout}
Vstep loadstep 0 PWL(0 0 50m 0 50.01m 1 70m 1 70.01m 0 100m 0)
Bload out 0 I=v(out)*({0.5*load/vo}+{0.5*load/vo}*v(loadstep))
Rbleed out 0 2200
Bmag mag 0 V=v(out)
Bphysical out_physical 0 V={'-' if negative else ''}v(out)
Bpk ipk 0 V=abs(i(Bpass))
.options reltol=0.001 abstol=1n vntol=1u method=gear
.save v(mag) v(ipk) v(set) v(vin) v(out_physical)
.tran 20u 100m 0 10u
{measures(vo,.05,.07,(.075,.079),.1)}
.end
'''


def make_cases(root=ROOT):
    a=analysis(root);v=a.native_values(root)
    assumptions=json.loads((root/'sim/power/assumptions.json').read_text())
    val=lambda ref:a.numeric(v[ref]);result=[]
    def append(name,kind,nominal,bindings,deck,**conditions):
        if kind!='ldo':conditions['expected_gate_duty']=nominal/conditions['vin'] if kind=='buck' else (nominal+.5)/(conditions['vin']+nominal+.5)
        result.append({'id':name,'kind':kind,'nominal_v':nominal,'bindings':{r:v[r] for r in bindings},
                       'vendor_model':False,'fidelity':'IMPOSED_DUTY_POWER_STAGE' if kind!='ldo' else 'MAGNITUDE_BEHAVIORAL_ENVELOPE',
                       'conditions':conditions,'deck':deck,'measures':MEASURES+(['gate_duty'] if kind!='ldo' else []),
                       'wave_signals':['v(mag)','v(ipk)','v(vin)']+(['v(gate)'] if kind!='ldo' else [])})
    for i,rail in enumerate(['6V2_PRE','3V3_D','1V8_D']):
        base=210+i*10
        refs=[f'R{base}',f'R{base+1}',f'L{201+i}',f'C{base+3}',f'C{base+4}']
        vo=a.divider(.8,val(refs[0]),val(refs[1]));load=assumptions['buck']['load_budget_a'][rail]
        for vin in assumptions['vin_prot_v']:
            deck=switching_deck('buck',vin,vo,load,val(refs[2]),0,val(refs[3])+val(refs[4]),False)
            append(f'buck_{rail}_{int(vin)}V','buck',vo,refs,deck,vin=vin,corner='native_nominal_L_C')
        deck=switching_deck('buck',15,vo,load,val(refs[2])*.8,0,20e-6,True)
        append(f'buck_{rail}_derated','buck',vo,refs,deck,vin=15,corner='L80pct_C20u_f450k_SENSITIVITY')
    vo=a.divider(.8,val('R410'),val('R411'))
    refs=['R410','R411','L301','L302','C410','C414','C415']
    for vin in assumptions['vin_prot_v']:
        deck=switching_deck('cuk',vin,vo,assumptions['cuk']['output_load_a'],val('L301'),val('L302'),val('C414')+val('C415'),False,val('C410'))
        append(f'cuk_{int(vin)}V','cuk',vo,refs,deck,vin=vin,corner='native_nominal_L_C')
    deck=switching_deck('cuk',15,vo,assumptions['cuk']['output_load_a'],val('L301')*.8,val('L302')*.8,10e-6,True,val('C410'))
    append('cuk_derated','cuk',vo,refs,deck,vin=15,corner='L80pct_C10u_f1.8M_SENSITIVITY')
    prereg=a.divider(.8,val('R210'),val('R211'))
    for tag,rs,cs,c1,c2,rlim,rail,k,neg in [
        ('5v0','R240','C240','C243','C244','R241','+5V0_DAC',150,False),
        ('5v2','R260','C260','C263','C264','R261','+5V2_PVDD',150,False),
        ('n5v2','R420','C420','C423','C424','R421','-5V2_PVSS',3750,True)]:
        if 'SET' not in v[cs]:raise ValueError('CSET binding no longer identifies SET capacitor: '+cs)
        for corner,iset,rf in [('low',98e-6,.999),('nominal',100e-6,1),('high',102e-6,1.001)]:
            target=val(rs)*rf*iset
            deck=ldo_deck(prereg if not neg else vo,target,assumptions['ldo']['load_budget_a'][rail],val(rs)*rf,val(cs),iset,k/val(rlim),neg,val(c1)+val(c2))
            append(f'ldo_{tag}_{corner}','ldo',target,[rs,cs,c1,c2,rlim],deck,corner=corner,negative=neg)
    return result


def assess(case,measured):
    delta=abs(measured['output_mean']-case['nominal_v'])/case['nominal_v']
    r={'qualification':'NOT_QUALIFIED','layout_allowed':False,'relative_mean_error':delta,
       'screen':'OUTSIDE_5_PERCENT_SCREEN' if delta>.05 else 'WITHIN_5_PERCENT_SCREEN',
       'interpretation':'Open-loop/behavioral case only; neither outcome is chip control-loop qualification.'}
    if 'expected_gate_duty' in case['conditions']:
        r['gate_duty_absolute_error']=abs(measured['gate_duty']-case['conditions']['expected_gate_duty'])
        r['solver_gate_ok']=r['gate_duty_absolute_error']<.001
    return r


def run_cases(cases,output,executable='ngspice',root=ROOT):
    exe=shutil.which(executable)
    if exe is None:raise FileNotFoundError('ngspice missing; simulation was NOT run')
    output.mkdir(parents=True,exist_ok=True)
    version=subprocess.run([exe,'--version'],capture_output=True,text=True,check=True,timeout=15).stdout
    results=[]
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    except (subprocess.SubprocessError,FileNotFoundError):commit='UNVERSIONED'
    for case in cases:
        path=output/case['id'];path.mkdir(exist_ok=True)
        (path/'bench.cir').write_text(case['deck'])
        wrapper=case['deck'].rsplit('.end',1)[0]+f'''
.control
set wr_singlescale
set wr_vecnames
run
wrdata waveform.dat {' '.join(case['wave_signals'])}
quit
.endc
.end
'''
        (path/'ngspice.cir').write_text(wrapper)
        invocation=[exe,'-b','-o','ngspice.log','ngspice.cir']
        completed=subprocess.run(invocation,cwd=path,capture_output=True,text=True,timeout=120)
        (path/'process.txt').write_text(completed.stdout+'\n'+completed.stderr)
        if completed.returncode:raise RuntimeError(f"{case['id']}: ngspice exit {completed.returncode}")
        logfile=path/'ngspice.log'
        if not logfile.is_file():raise ValueError('missing simulator log')
        measured=parse_measures(logfile.read_text(),case['measures']);assessment=assess(case,measured)
        if assessment.get('solver_gate_ok') is False:raise ValueError('simulated PWM duty differs from imposed duty: '+case['id'])
        waveform=path/'waveform.dat'
        if not waveform.is_file() or waveform.stat().st_size<100:raise ValueError('missing/empty waveform')
        row={k:v for k,v in case.items() if k!='deck'}
        row.update(measured=measured,assessment=assessment,
                   deck_sha256=hashlib.sha256(case['deck'].encode()).hexdigest(),
                   executable=exe,command=invocation,
                   artifact_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (path/'bench.cir',path/'ngspice.cir',logfile,waveform)})
        results.append(row)
        print(case['id'],json.dumps(measured),flush=True)
        (output/'results.json').write_text(json.dumps({'status':'PARTIAL','cases':results},indent=2)+'\n')
    report={'status':'EXECUTED_NOT_QUALIFIED','layout_allowed':False,'source_commit':commit,
            'source_digest':analysis(root).content_digest(root),'simulator_version':version,'cases':results,
            'vendor_model_cases':0,'bench_measurements':0}
    (output/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    lines=['# Portable SPICE results — not manufacturer simulation','',
           'Status: EXECUTED_NOT_QUALIFIED. All cases use imposed-duty stages or LDO envelopes.',
           '', '| Case | Mean V | Ripple Vpp | Peak A | Startup s | Screen |', '|---|---:|---:|---:|---:|---|']
    for r in results:
        m=r['measured'];lines.append(f"| {r['id']} | {m['output_mean']:.5g} | {m['ripple_v']:.4g} | {m['current_peak']:.4g} | {m['startup_s']:.4g} | {r['assessment']['screen']} |")
    (output/'results.md').write_text('\n'.join(lines)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/edv/spice')
    p.add_argument('--emit-only',action='store_true')
    p.add_argument('--case',help='exact case ID, otherwise run full matrix')
    a=p.parse_args()
    try:
        cases=make_cases(ROOT)
        if a.case:
            cases=[c for c in cases if c['id']==a.case]
            if not cases:raise ValueError('unknown case')
        if a.emit_only:
            a.output.mkdir(parents=True,exist_ok=True)
            for c in cases:(a.output/(c['id']+'.cir')).write_text(c['deck'])
            print('EMITTED_NOT_RUN',len(cases));return 0
        report=run_cases(cases,a.output)
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print('SPICE INCOMPLETE:',exc,file=sys.stderr);return 1
    print('Executed:',len(report['cases']),'; vendor model cases: 0; hardware qualification: NOT_QUALIFIED')
    return 0


if __name__=='__main__':raise SystemExit(main())
