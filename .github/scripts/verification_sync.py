#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, os, re, sys, urllib.error, urllib.request
from typing import Any

API_VERSION=os.getenv("NOTION_API_VERSION","2026-03-11")
FIELDS={"REQ-ID":"req_id","TC-ID":"tc_id","Knowledge Node URL":"node_url","Requirement":"requirement",
"Test Case":"test_case","Verification Level":"level","Acceptance Criteria":"acceptance","Evidence Path":"evidence_path",
"Evidence URL":"evidence_url","Bench / DUT":"bench","HW Revision":"hw","FW SHA":"fw","Bitstream":"bitstream",
"Result":"result","Verification Status":"status"}
LEVELS={"software":"软件/单元","unit":"软件/单元","软件/单元":"软件/单元","rtl":"仿真/RTL","simulation":"仿真/RTL",
"仿真/RTL":"仿真/RTL","hil":"HIL/台架","bench":"HIL/台架","HIL/台架":"HIL/台架","physical":"实机",
"hardware":"实机","实机":"实机","dv":"DV","DV":"DV","pv":"PV","PV":"PV","eol":"EOL","EOL":"EOL"}
RESULTS={"PASS","FAIL","PARTIAL","BLOCKED","NOT RUN"}
STATUSES={"Planned","Ready","Running","Verified","Blocked"}
REPOS={"magic-alt/hil_lab":"hil_lab","magic-alt/igh-lab":"igh-lab","magic-alt/servo_host":"servo_host","magic-alt/servoHIL":"servoHIL"}
EMPTY={"","n/a","na","none","-","tbd","todo","not applicable","_no response_","no response"}

def clean(v):
    if v is None:return ""
    v=re.sub(r"<!--.*?-->","",str(v),flags=re.S).strip().strip(chr(96)+" ")
    return "" if v.lower() in EMPTY else v

def parse(body):
    text=body or ""; rx=re.compile(r"^(#{1,6})\s+(.+?)\s*$",re.M); ms=list(rx.finditer(text)); out={}
    for i,m in enumerate(ms):
        if len(m.group(1))!=3:continue
        key=FIELDS.get(m.group(2).strip())
        if key:
            end=ms[i+1].start() if i+1<len(ms) else len(text)
            out[key]=clean(text[m.end():end])
    return out

def normalize(m):
    o=dict(m); level=clean(o.get("level"))
    if level:
        level=LEVELS.get(level,LEVELS.get(level.lower()))
        if not level:raise ValueError("unsupported Verification Level")
        o["level"]=level
    result=clean(o.get("result")).upper()
    if result:
        if result not in RESULTS:raise ValueError("unsupported Result")
        o["result"]=result
    status=clean(o.get("status"))
    if status and status not in STATUSES:raise ValueError("unsupported Verification Status")
    if result and not status:o["status"]={"PASS":"Verified","FAIL":"Verified","PARTIAL":"Ready","BLOCKED":"Blocked","NOT RUN":"Planned"}[result]
    return o

def tracked(m):
    req,tc=clean(m.get("req_id")),clean(m.get("tc_id"))
    if not req and not tc:return False
    if not req or not tc:raise ValueError("REQ-ID and TC-ID must both be set or both be n/a")
    if not re.fullmatch(r"REQ-[A-Z0-9][A-Z0-9-]*",req):raise ValueError("invalid REQ-ID")
    if not re.fullmatch(r"TC-[A-Z0-9][A-Z0-9-]*",tc):raise ValueError("invalid TC-ID")
    return True

def pid(url):
    raw=url.replace("-",""); m=re.search(r"([0-9a-fA-F]{32})(?:\?|$)",raw)
    if not m:raise ValueError("Knowledge Node URL must contain a Notion page id")
    h=m.group(1).lower(); return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

def rt(v):return {"rich_text":[{"type":"text","text":{"content":v[:2000]}}]}
def tt(v):return {"title":[{"type":"text","text":{"content":v[:2000]}}]}
def sl(v):return {"select":{"name":v}}
def ul(v):return {"url":v or None}
def da(v):return {"date":{"start":v}}

def entity(ev):
    repo=ev.get("repository",{}).get("full_name","")
    if "pull_request" in ev:
        p=ev["pull_request"]; state="merged" if p.get("merged") or p.get("merged_at") else p.get("state","open")
        return {"type":"PR","number":p.get("number") or ev.get("number"),"url":p.get("html_url",""),"body":p.get("body") or "",
        "title":p.get("title",""),"state":state,"repo":repo,"sha":p.get("head",{}).get("sha",""),"updated":p.get("updated_at") or ""}
    if "issue" in ev and not ev["issue"].get("pull_request"):
        i=ev["issue"]; return {"type":"Issue","number":i.get("number"),"url":i.get("html_url",""),"body":i.get("body") or "",
        "title":i.get("title",""),"state":i.get("state","open"),"repo":repo,"sha":"","updated":i.get("updated_at") or ""}
    return None

def props(e,m):
    p={"Issue/PR":ul(e["url"]),"GitHub Type":sl(e["type"]),"GitHub Number":{"number":e["number"]},
       "GitHub State":sl(e["state"]),"Last Synced":da(dt.datetime.now(dt.timezone.utc).date().isoformat())}
    if e["repo"] in REPOS:p["Repository"]=sl(REPOS[e["repo"]])
    for k,n in [("requirement","Requirement"),("test_case","Test Case"),("acceptance","Acceptance Criteria"),("bench","Bench / DUT")]:
        if clean(m.get(k)):p[n]=rt(m[k])
    if clean(m.get("level")):p["验证层级"]=sl(m["level"])
    if clean(m.get("result")):p["Result"]=sl(m["result"])
    if clean(m.get("status")):p["Verification Status"]=sl(m["status"])
    cfg=[]
    if e["type"]=="PR" and e.get("sha"):cfg.append("git="+e["sha"])
    for k,n in [("fw","fw"),("bitstream","bitstream"),("hw","hw")]:
        if clean(m.get(k)):cfg.append(n+"="+m[k])
    if cfg:p["Commit/FW/Bitstream"]=rt("; ".join(cfg))
    evidence=[]
    if clean(m.get("evidence_path")):evidence.append("path="+m["evidence_path"])
    if clean(m.get("hw")):evidence.append("hw="+m["hw"])
    if evidence:p["Evidence"]=rt("; ".join(evidence))
    if clean(m.get("evidence_url")):p["Evidence URL"]=ul(m["evidence_url"])
    if clean(m.get("result")) in {"PASS","FAIL","PARTIAL"}:p["Evidence Date"]=da((e.get("updated") or "")[:10] or dt.date.today().isoformat())
    return p

class Notion:
    def __init__(self,token,ds):self.token,self.ds=token,ds
    def req(self,method,path,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        q=urllib.request.Request("https://api.notion.com/v1/"+path,data=data,method=method,
          headers={"Authorization":"Bearer "+self.token,"Notion-Version":API_VERSION,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(q,timeout=30) as r:return json.load(r)
        except urllib.error.HTTPError as x:raise RuntimeError("Notion API %s: %s"%(x.code,x.read().decode(errors="replace"))) from x
    def find(self,req_id,tc_id):
        f={"and":[{"property":"Requirement ID","rich_text":{"equals":req_id}},{"property":"Test Case ID","rich_text":{"equals":tc_id}}]}
        return self.req("POST","data_sources/"+self.ds+"/query",{"filter":f,"page_size":10}).get("results",[])
    def update(self,page_id,p):return self.req("PATCH","pages/"+page_id,{"properties":p})
    def create(self,e,m,p):
        node=clean(m.get("node_url"))
        if not node:raise ValueError("missing Matrix row and Knowledge Node URL")
        cp={"验证项":tt(m["req_id"]+" / "+m["tc_id"]+" — "+e["title"][:120]),"Knowledge Node":{"relation":[{"id":pid(node)}]},
            "Requirement ID":rt(m["req_id"]),"Test Case ID":rt(m["tc_id"]),**p}
        return self.req("POST","pages",{"parent":{"type":"data_source_id","data_source_id":self.ds},"properties":cp})

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--event",required=True); a=ap.parse_args()
    with open(a.event,encoding="utf-8") as f:ev=json.load(f)
    e=entity(ev)
    if not e:print("verification-sync: unsupported event");return 0
    m=normalize(parse(e["body"]))
    if not tracked(m):print("verification-sync: not Matrix-managed");return 0
    p=props(e,m); token=os.getenv("NOTION_TOKEN",""); ds=os.getenv("NOTION_VERIFICATION_DATA_SOURCE_ID","")
    if not token or not ds:
        print("verification-sync: metadata valid; Notion sync skipped (secret/variable not configured)")
        print(json.dumps({"entity":e,"metadata":m},ensure_ascii=False,indent=2));return 0
    n=Notion(token,ds); hits=n.find(m["req_id"],m["tc_id"])
    if len(hits)>1:raise RuntimeError("duplicate Matrix rows for REQ-ID/TC-ID")
    page=n.update(hits[0]["id"],p) if hits else n.create(e,m,p)
    print("verification-sync: %s Matrix page %s"%("updated" if hits else "created",page.get("id","")));return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,RuntimeError) as x:print("verification-sync: ERROR: "+str(x),file=sys.stderr);raise SystemExit(2)
