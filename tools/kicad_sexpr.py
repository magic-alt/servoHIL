"""Small strict S-expression reader for native KiCad review tooling (not an EDA engine)."""
from __future__ import annotations
import json
import re

class Atom(str):
    pass

def parse(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',text)
    stack=[];root=None
    for token in tokens:
        if token=='(':
            value=[]
            if stack: stack[-1].append(value)
            elif root is not None: raise ValueError('multiple S-expression roots')
            else: root=value
            stack.append(value)
        elif token==')':
            if not stack: raise ValueError('unbalanced close')
            stack.pop()
        else:
            if not stack: raise ValueError('atom outside root')
            stack[-1].append(json.loads(token) if token.startswith('"') else Atom(token))
    if stack or root is None: raise ValueError('incomplete S-expression')
    return root

def dump(node):
    if isinstance(node,list): return '('+' '.join(dump(v) for v in node)+')'
    if isinstance(node,Atom): return str(node)
    return json.dumps(node,ensure_ascii=False)

def document(node):
    return '('+str(node[0])+'\n'+'\n'.join('  '+dump(x) for x in node[1:])+'\n)\n'

def items(node,tag):
    return [v for v in node if isinstance(v,list) and v and v[0]==tag]

def one(node,tag,default=None):
    return next(iter(items(node,tag)),default)

def walk(node,tag):
    if not isinstance(node,list): return
    if node and node[0]==tag: yield node
    for child in node:
        if isinstance(child,list): yield from walk(child,tag)

def expr(text): return parse(text)

def number(value):
    return Atom(f'{float(value):.4f}'.rstrip('0').rstrip('.') if float(value) else '0')
