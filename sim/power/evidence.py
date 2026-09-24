#!/usr/bin/env python3
"""Verify complete, source-bound simulation evidence; NOT hardware approval.

An integrity check cannot authenticate a simulator or replace independent bench
measurement. It rejects accidental stale/mixed/partial/tampered evidence packs.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
ARTIFACTS={'bench.cir','ngspice.cir','process.txt','ngspice.log','waveform.dat'}


def spice(root):
    spec=importlib.util.spec_from_file_location('edv_integrity_spice',root/'sim/power/spice.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def expected_cases(root):
    return spice(root).make_cases(root)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def verify(directory,root=ROOT,expected_source_commit=None):
    directory=Path(directory).resolve();root=Path(root).resolve()
    r=json.loads((directory/'results.json').read_text())
    s=spice(root)
    if (r.get('status')!='EXECUTED_NOT_QUALIFIED' or r.get('layout_allowed') is not False
            or r.get('source_worktree_dirty') is not False):
        raise ValueError('not a complete clean-worktree, non-qualified run')
    if not re.fullmatch(r'[0-9a-f]{40}',r.get('source_commit','')):
        raise ValueError('unversioned simulation source')
    if expected_source_commit is not None and r['source_commit']!=expected_source_commit:
        raise ValueError('source commit mismatch')
    if r.get('source_digest')!=s.analysis(root).content_digest(root):
        raise ValueError('source digest mismatch; rerun against this source')
    cases=expected_cases(root);ids=[c['id'] for c in cases]
    rows=r.get('cases',[]);actual=[c['id'] for c in rows]
    if (not ids or sorted(actual)!=sorted(ids) or r.get('planned_case_ids')!=ids
            or r.get('completed_case_count')!=len(ids)):
        raise ValueError('incomplete/duplicate/unexpected simulation matrix')
    if r.get('vendor_model_cases')!=0 or r.get('bench_measurements')!=0:
        raise ValueError('portable simulation cannot claim vendor/bench evidence')
    byid={c['id']:c for c in rows}
    for case in cases:
        row=byid[case['id']];path=(directory/case['id']).resolve()
        if not path.is_relative_to(directory):raise ValueError('case escapes evidence directory')
        for key,value in case.items():
            if key!='deck' and row.get(key)!=value:raise ValueError('case metadata mismatch: '+key)
        if set(row.get('artifact_sha256',{}))!=ARTIFACTS:
            raise ValueError('missing or unexpected artifact names')
        for name,expected in row['artifact_sha256'].items():
            file=(path/name).resolve()
            if not file.is_relative_to(path) or not file.is_file() or digest(file)!=expected:
                raise ValueError('artifact missing/hash mismatch: '+case['id']+'/'+name)
        deckhash=hashlib.sha256(case['deck'].encode()).hexdigest()
        if row.get('deck_sha256')!=deckhash or digest(path/'bench.cir')!=deckhash:
            raise ValueError('deck differs from current native-bound bench')
        measured=s.parse_measures((path/'ngspice.log').read_text(),case['measures'])
        if row.get('measured')!=measured:raise ValueError('JSON measures disagree with raw log')
        assessment=s.assess(case,measured)
        if row.get('assessment')!=assessment or assessment.get('solver_gate_ok') is False:
            raise ValueError('assessment or numerical-duty gate mismatch')
    return {'integrity':'VERIFIED_NOT_QUALIFIED','layout_allowed':False,
            'source_commit':r['source_commit'],'source_digest':r['source_digest'],
            'case_count':len(rows),'artifact_count':len(rows)*len(ARTIFACTS),
            'outside_output_screen':[c['id'] for c in rows if c['assessment']['screen']=='OUTSIDE_5_PERCENT_SCREEN'],
            'manifest_sha256':digest(directory/'results.json'),
            'scope':'Checks byte identity, matrix/deck binding and log/JSON consistency, not electrical qualification.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--expected-source-commit')
    args=p.parse_args()
    try:r=verify(args.directory,args.root,args.expected_source_commit)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('EVIDENCE INTEGRITY FAILED:',exc,file=sys.stderr);return 1
    print(json.dumps(r,indent=2,allow_nan=False));return 0


if __name__=='__main__':raise SystemExit(main())
