#!/usr/bin/env python3
"""Native-value ADC/PHY screening; NEVER a physical or manufacturing PASS.

Vendor bases: AD7606C-16 Rev.A supply/current/Rin tables; THVD1450 Rev.E
DC table (3 mA is *no-load* current, 250 mA is short-circuit magnitude).
Source resistor tolerance, remote termination, dynamic reserve and retained
pre-PR22 loads below are explicit engineering assumptions, not vendor evidence.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('peripheral_power',ROOT/'sim/power/analysis.py')
power=importlib.util.module_from_spec(spec);spec.loader.exec_module(power)


def rc_screen(rpos:float,rneg:float,cap:float)->dict:
    power.positive(rpos,rneg,cap)
    tau=(rpos+rneg)*cap
    gain_loss=rpos/(1e6+rpos)
    return {'series_positive_ohm':rpos,'series_negative_ohm':rneg,'differential_cap_f':cap,
            'external_rc_pole_hz':1/(2*math.pi*tau),
            'nyquist_500khz_attenuation_db':-10*math.log10(1+(2*math.pi*500e3*tau)**2),
            'external_full_step_half_lsb_s':math.log(2**17)*tau,
            'dc_gain_loss_ppm_screen':1e6*gain_loss,
            'positive_endpoint_error_lsb_screen':10*gain_loss/(20/65536),
            'model':'external RC only; simplified 1Mohm positive-leg DC load; internal ADC errors/filter excluded'}


def driver_screen(vcc:float,termination:float)->dict:
    power.positive(vcc,termination)
    # Two equal end terminations at -1% tolerance; 54 ohm is also screened
    # as the standard loaded-driver test case. Cable/node/fault loads differ.
    resistance=min(54.0,termination*.99/2)
    loaded=vcc/resistance+.003
    return {'native_termination_ohm':termination,'effective_load_screen_ohm':resistance,
            'loaded_current_screen_a':loaded,'quiescent_no_load_max_a':.003,
            'local_termination_power_screen_w':vcc*vcc/(termination*.99),
            'short_circuit_magnitude_a':.25,
            'model':'VCC/R plus no-load Icc; dynamic losses and simultaneous fault energy not qualified'}


def build_report(root:Path=ROOT)->dict:
    values=power.native_values(root)
    for ref,expected in [('U801','AD7606C-16BSTZ'),('U1010','SN74LVC541APWR')]+[
            (r,'THVD1450DR') for r in ('U901','U902','U903','U904','U1001')]:
        if values.get(ref)!=expected:raise ValueError('device/model binding changed: '+ref)
    def val(ref):return power.numeric(values[ref])
    a=json.loads((root/'sim/power/assumptions.json').read_text())
    main=power.build_report(root)
    avcc=main['ldos']['+5V0_DAC']['magnitude_limits_v']
    vdrive=main['bucks']['1V8_D']['static_limits_v']
    vcc=main['bucks']['3V3_D']['static_limits_v']
    channels=[{'channel':i,**rc_screen(val(f'R{850+2*i}'),val(f'R{851+2*i}'),val(f'C{850+i}'))} for i in range(8)]
    drivers=[{'ref':ref,**driver_screen(vcc[1],val(resistor))} for ref,resistor in
             [('U901','R950'),('U902','R951'),('U903','R952'),('U904','R953'),('U1001','R1006')]]
    load=sum(d['loaded_current_screen_a'] for d in drivers)
    # Retain the entire earlier 0.3 A allocation, even if it contained spare
    # capacity: conservative additive reservation, not a measured baseline.
    allocation=.3+load+.020+.005
    allocated={'3V3_D':a['buck']['load_budget_a']['3V3_D'],
               '1V8_D':a['buck']['load_budget_a']['1V8_D'],
               '6V2_PRE':a['buck']['load_budget_a']['6V2_PRE'],
               '+5V0_DAC':a['ldo']['load_budget_a']['+5V0_DAC']}
    budget_ok=(allocated['3V3_D']>=allocation and allocated['1V8_D']>=.3019 and
               allocated['6V2_PRE']>=.55 and allocated['+5V0_DAC']>=.25)
    blockers=set(main['blocker_ids'])|{'ACTUAL_DUT_ADAPTER_INHIBIT','ADC_INPUT_ENERGY_AND_ESD',
             'ADC_CALIBRATION_AND_ALIAS_FILTER','ADC_SERIAL_TIMING_AND_LANE_MAPPING',
             'PHY_CABLE_TERMINATION_AND_CONTENTION','PHY_LOADED_DYNAMIC_AND_FAULT_THERMAL',
             'AON_SAFETY_LOAD_AND_THERMAL','PARTIAL_POWER_AND_BACKFEED',
             'CAPACITOR_MPN_DC_BIAS','PACKAGE_CONNECTOR_REVIEW','BOARD_MEASUREMENTS'}
    if not budget_ok:blockers.add('PERIPHERAL_POWER_BUDGET_NOT_ALLOCATED')
    static_supply_ok=(4.75<=avcc[0]<=avcc[1]<=5.25 and 1.71<=vdrive[0]<=vdrive[1]<=5.25)
    if not static_supply_ok:blockers.add('ADC_STATIC_SUPPLY_OUT_OF_RANGE')
    return {'scope':'NATIVE_VALUE_ANALYTICAL_SCREEN_ONLY','qualification':'BLOCKED',
            'layout_allowed':False,'physical_tests':'NOT_RUN','source_digest':power.content_digest(root),
            'adc':{'avcc_v':avcc,'vdrive_v':vdrive,'static_supply_screen_pass':static_supply_ok,
                   'max_avcc_operating_current_a':.050,'max_vdrive_operating_current_a':.0019,
                   'current_test_basis':'AD7606C-16 1MSPS datasheet table; not board measurement',
                   'rc_channels':channels},
            'phy':{'vcc_v':vcc,'drivers':drivers,'all_enabled_resistive_load_screen_a':load,
                   'new_3v3_provisional_allocation_a':allocation,
                   'retained_previous_3v3_budget_a':.3,'dynamic_reserve_assumed_a':.020,
                   'logic_and_pull_reserve_assumed_a':.005,
                   'simultaneous_short_plus_retained_budget_screen_a':.3+5*.25,
                   'normal_role_note':'Normally two encoder TX pairs plus optional RS485; five enabled is a stress case, not an approved role'},
            'allocated_loads_a':allocated,'power_budget_allocated':budget_ok,
            'blockers':sorted(blockers),
            'references':['https://www.analog.com/media/en/technical-documentation/data-sheets/ad7606c-16.pdf',
                          'https://www.ti.com/lit/ds/symlink/thvd1450.pdf']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--strict-design',action='store_true')
    args=parser.parse_args()
    report=build_report();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(f"Peripheral screening: {report['qualification']}; layout_allowed=false; {len(report['blockers'])} open blockers")
    return 2 if args.strict_design else 0

if __name__=='__main__':raise SystemExit(main())
