#!/usr/bin/env python3
"""Portable ngspice/LTspice screening, explicitly NOT vendor macro-models.

Generated .cir files contain portable analysis directives. The ngspice-only
.control wrapper is separate. No proprietary vendor models are redistributed.
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


def analysis(root):
    spec=importlib.util.spec_from_file_location('edv_analysis_spice',root/'sim/power/analysis.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def parse_measures(log, requested):
    if re.search(r'(?im)^\s*(?:error\b|fatal\b)|measure.*failed|timestep too small|simulation interrupted',log):
        raise ValueError('SPICE reports an error/failed measurement')
    result={}
    for key in requested:
        rows=re.findall(r'(?im)^\s*'+re.escape(key)+r'\s*=\s*(\S+)',log)
        if len(rows)!=1:
            raise ValueError(f'measure {key}: expected once, found {len(rows)}')
        try: value=float(rows[0])
        except ValueError as exc: raise ValueError('invalid SPICE measure '+key) from exc
        if not math.isfinite(value):raise ValueError('nonfinite SPICE measure '+key)
        result[key]=value
    return result


def measures(nominal, before, step, release, settled, shutdown, end):
    return f'''
.meas tran output_mean AVG v(mag) FROM={settled[0]} TO={settled[1]}
.meas tran ripple_v PP v(mag) FROM={settled[0]} TO={settled[1]}
.meas tran current_peak MAX v(ipk) FROM=0 TO={end}
.meas tran startup_s WHEN v(mag)={0.9*nominal} RISE=1
.meas tran step_min MIN v(mag) FROM={step} TO={release}
.meas tran step_max MAX v(mag) FROM={release} TO={settled[1]}
.meas tran shutdown_v FIND v(mag) AT={end}
'''


MEASURES=['output_mean','ripple_v','current_peak','startup_s','step_min','step_max','shutdown_v']


def switching_deck(kind,vin,vo,load,l1,l2,cap,derated):
    """Actual L/C/switch network with imposed duty. NO internal chip controller."""
    if kind=='buck':
        freq=450000 if derated else 500000
        ramp=.004;step=.007;release=.010;off=.012;end=.018
        settle=(.011,.0119);dt=1/(freq*30)
        duty=vo/vin
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
Bload out 0 I=v(out)*({0.5*load/vo}+{0.5*load/vo}*v(loadstep))
'''
    else:
        freq=1800000 if derated else 2000000
        ramp=.0004;step=.0009;release=.0015;off=.0022;end=.003
        settle=(.0019,.0021);dt=1/(freq*30)
        duty=(vo+.5)/(vin+vo+.5)
        network=f'''
.model SWMOD SW(Ron=0.3 Roff=1e9 Vt=0.5 Vh=0.02)
.model SCHOTTKY D(Is=1u Rs=0.08 N=1.1)
Rinput vin li1 0.1
Linput li1 sw {l1}
Vsense sw swsense 0
Smain swsense 0 gate 0 SWMOD
Ctransfer sw xcap 1u
Rtransfer xcap negx 0.03
Dfly negx 0 SCHOTTKY
Routput negx li2 0.1
Loutput li2 out {l2}
Bmag mag 0 V=-v(out)
Bpk ipk 0 V=abs(i(Vsense))
Bload out 0 I=v(out)*({0.5*load/vo}+{0.5*load/vo}*v(loadstep))
'''
    text=f'''EDV {kind} SWITCHED POWER STAGE - NOT A VENDOR MODEL
* Open-loop imposed duty; startup ramp and load step are test stimuli, not IC behavior.
* DOES NOT verify internal compensation, soft start, current limit, hiccup or thermal protection.
* Ron/ESR/DCR/diode are screening assumptions; actual parasitics/AC losses unqualified.
Vbus vin 0 PWL(0 0 100u {vin} {end} {vin})
Venable enable 0 PWL(0 1 {off} 1 {off+1e-6} 0 {end} 0)
Vduty duty 0 PWL(0 0 100u 0 {ramp} {duty} {off} {duty} {off+1e-6} 0 {end} 0)
Vsaw saw 0 PULSE(0 1 0 {1/freq-2e-9} 1n 1n {1/freq})
Bdrive gate 0 V=(v(saw)<v(duty))*(v(enable)>0.5)
Vstep loadstep 0 PWL(0 0 {step} 0 {step+2e-6} 1 {release} 1 {release+2e-6} 0 {end} 0)
{network}
Resr out cout 0.02
Cout cout 0 {cap}
Rbleed out 0 2200
.options reltol=0.001 abstol=1n vntol=1u method=gear
.save v(mag) v(out) v(ipk) v(vin) v(gate)
.tran {dt*5} {end} 0 {dt}
'''
    text+=measures(vo,0,step,release,settle,off,end)+'.end\n'
    return text


def ldo_deck(vin,vo,load,rset,cset,iset,limit,negative=False):
    """Magnitude-domain envelope. Negative LDO NOT modeled as a real LT3094."""
    return f'''EDV LDO ENVELOPE - NOT A VENDOR MODEL
* RSET/CSET taken from native circuit. Ideal gm follower with assumed dropout/current clamp.
* Fast-start current and gm are assumptions. No loop/PSRR/noise/thermal/reverse-current validation.
* negative={negative}: magnitude domain; out_physical is a sign-restored probe ONLY.
Vbus vin 0 PWL(0 0 5m {vin} 80m {vin} 80.1m 0 100m 0)
Biset 0 set I=(v(vin)>2)*({iset}+(v(set)<{vo*.95})*0.0018)
Rset set 0 {rset}
Cset set 0 {cset}
Bpass vin out I=max(0,min({limit},20*(min(v(set),max(v(vin)-0.45,0))-v(out))))
Ignd vin 0 0.003
Resr out cap 0.02
Cout cap 0 20u
Vstep loadstep 0 PWL(0 0 50m 0 50.01m 1 70m 1 70.01m 0 100m 0)
Bload out 0 I=v(out)*({0.5*load/vo}+{0.5*load/vo}*v(loadstep))
Rbleed out 0 2200
Bmag mag 0 V=v(out)
Bphysical out_physical 0 V={'-' if negative else ''}v(out)
Bpk ipk 0 V=abs(i(Bpass))
.options reltol=0.001 abstol=1n vntol=1u method=gear
.save v(mag) v(ipk) v(set) v(vin) v(out_physical)
.tran 20u 100m 0 10u
{measures(vo,0,.05,.07,(.075,.079),.08,.1)}
.end
'''


def make_cases(root=ROOT):
    a=analysis(root);v=a.native_values(root)
    assumptions=json.loads((root/'sim/power/assumptions.json').read_text())
    val=lambda ref:a.numeric(v[ref])
    result=[]
    def append(name,kind,nominal,bindings,deck,**conditions):
        result.append({'id':name,'kind':kind,'nominal_v':nominal,'bindings':{r:v[r] for r in bindings},
                       'vendor_model':False,'fidelity':'IMPOSED_DUTY_POWER_STAGE' if kind!='ldo' else 'MAGNITUDE_BEHAVIORAL_ENVELOPE',
                       'conditions':conditions,'deck':deck,'measures':MEASURES,
                       'wave_signals':['v(mag)','v(ipk)','v(vin)']})
    for i,rail in enumerate(['6V2_PRE','3V3_D','1V8_D']):
        refs=[f'R{210+i*10}',f'R{211+i*10}',f'L{201+i}']
        vo=a.divider(.8,val(refs[0]),val(refs[1]));load=assumptions['buck']['load_budget_a'][rail]
        for vin in assumptions['vin_prot_v']:
            deck=switching_deck('buck',vin,vo,load,val(refs[2]),0,44e-6,False)
            append(f'buck_{rail}_{int(vin)}V','buck',vo,refs,deck,vin=vin,corner='nominal_L_C')
        deck=switching_deck('buck',15,vo,load,val(refs[2])*.8,0,20e-6,True)
        append(f'buck_{rail}_derated','buck',vo,refs,deck,vin=15,corner='L80pct_C20u_f450k_SENSITIVITY')
    vo=a.divider(.8,val('R410'),val('R411'))
    for vin in assumptions['vin_prot_v']:
        deck=switching_deck('cuk',vin,vo,assumptions['cuk']['output_load_a'],val('L301'),val('L302'),20e-6,False)
        append(f'cuk_{int(vin)}V','cuk',vo,['R410','R411','L301','L302','C410'],deck,vin=vin,corner='nominal_L_C')
    deck=switching_deck('cuk',15,vo,assumptions['cuk']['output_load_a'],val('L301')*.8,val('L302')*.8,10e-6,True)
    append('cuk_derated','cuk',vo,['R410','R411','L301','L302','C410'],deck,vin=15,corner='L80pct_C10u_f1.8M_SENSITIVITY')
    for tag,rs,cs,rail,limit,neg in [('5v0','R240','C241','+5V0_DAC',.3,False),
                                    ('5v2','R260','C261','+5V2_PVDD',.3,False),
                                    ('n5v2','R420','C420','-5V2_PVSS',.25,True)]:
        # CSET reference mapping must match the actual native value; reject stale mapping.
        cset=val(cs)
        if not 1e-9<=cset<=10e-6:raise ValueError('unreasonable CSET binding '+cs)
        for corner,iset,rf in [('low',98e-6,.999),('nominal',100e-6,1),('high',102e-6,1.001)]:
            target=val(rs)*rf*iset
            deck=ldo_deck(6.184 if not neg else vo,target,assumptions['ldo']['load_budget_a'][rail],val(rs)*rf,cset,iset,limit,neg)
            append(f'ldo_{tag}_{corner}','ldo',target,[rs,cs],deck,corner=corner,negative=neg)
    return result


def assess(case,measured):
    vo=case['nominal_v']
    delta=abs(measured['output_mean']-vo)/vo
    return {'qualification':'NOT_QUALIFIED','layout_allowed':False,
            'relative_mean_error':delta,
            'screen':'OUTSIDE_5_PERCENT_SCREEN' if delta>.05 else 'WITHIN_5_PERCENT_SCREEN',
            'interpretation':'Open-loop/behavioral case only. Neither outcome is chip control-loop qualification.'}


def run_cases(cases,output,executable='ngspice',root=ROOT):
    exe=shutil.which(executable)
    if exe is None:raise FileNotFoundError('ngspice missing; simulation was NOT run')
    output.mkdir(parents=True,exist_ok=True)
    version=subprocess.run([exe,'--version'],capture_output=True,text=True,check=True,timeout=15).stdout
    results=[]
    try: commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
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
        measured=parse_measures(logfile.read_text(),case['measures'])
        waveform=path/'waveform.dat'
        if not waveform.is_file() or waveform.stat().st_size<100:raise ValueError('missing/empty waveform')
        row={k:v for k,v in case.items() if k!='deck'}
        row.update(measured=measured,assessment=assess(case,measured),
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
           'Status: EXECUTED_NOT_QUALIFIED. All decks are open-loop switching stages or LDO envelopes.',
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
