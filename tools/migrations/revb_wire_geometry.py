"""Normalize explicit wire geometry without changing any pin or label anchor.

Split/union same-net collinear segments, retain all component and label terminals,
and remove only degree-one tails with no electrical terminal. Actual KiCad graph
comparison remains mandatory after this transformation.
"""
from collections import defaultdict
from kicad_sexpr import parse,one


def clean(editor):
    def key(p):return (round(p[0],6),round(p[1],6))
    def on(p,a,b):
        return (a[0]==b[0]==p[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or (a[1]==b[1]==p[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0]))
    grouped=defaultdict(list);terminals=defaultdict(set)
    for net,a,b in editor.lines:
        a,b=key(a),key(b)
        if a!=b:grouped[net].append((a,b))
    for ref in editor.placed:
        for pin in editor.pins(ref):
            net=editor.expected.get(ref+'.'+pin)
            if net is not None:terminals[net].add(key(editor.pt(ref,pin)))
    for item in editor.elements:
        if item[0] in ('label','global_label'):
            at=one(item,'at');terminals[str(item[1])].add(key((float(at[1])/2.54,float(at[2])/2.54)))
        elif item[0]=='symbol' and one(item,'lib_id',['',''])[1]=='RevB:GND':
            at=one(item,'at');terminals['GND'].add(key((float(at[1])/2.54,float(at[2])/2.54)))
    result=[];pruned=0
    for net,segments in grouped.items():
        points=set(terminals[net])
        for a,b in segments:points.update((a,b))
        for a,b in segments:
            for c,d in segments:
                if a[0]==b[0] and c[1]==d[1]:
                    p=(a[0],c[1])
                    if on(p,a,b) and on(p,c,d):points.add(p)
        edges=set()
        for a,b in segments:
            inside=sorted(p for p in points if on(p,a,b))
            for p,q in zip(inside,inside[1:]):
                if p!=q:edges.add((p,q))
        while True:
            degree=defaultdict(int)
            for a,b in edges:degree[a]+=1;degree[b]+=1
            loose={p for p,count in degree.items() if count==1 and p not in terminals[net]}
            if not loose:break
            removed={edge for edge in edges if any(p in loose for p in edge)}
            if not removed:break
            pruned+=len(removed);edges-=removed
        for a,b in sorted(edges):result.append((net,a,b))
    editor.lines=result
    editor.elements=[x for x in editor.elements if x[0] not in ('wire','junction')]
    for net,a,b in result:
        editor.elements.append(parse(f'(wire (pts (xy {editor.mm(a)}) (xy {editor.mm(b)})) (stroke (width 0) (type default)) (uuid "{editor.uid()}"))'))
    degree=defaultdict(lambda:defaultdict(int))
    for net,a,b in result:degree[net][a]+=1;degree[net][b]+=1
    for net,nodes in degree.items():
        for p,count in nodes.items():
            if count>2:editor.elements.append(parse(f'(junction (at {editor.mm(p)}) (diameter 0) (color 0 0 0 0) (uuid "{editor.uid()}"))'))
    print(editor.name,': explicit wire segments',len(result),'pinless tails removed',pruned)
