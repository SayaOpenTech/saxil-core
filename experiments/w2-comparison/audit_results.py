"""Second-pass byte/semantic audit; does not import the measurement runner.

JSON decoding below is separate from the benchmark decoder. It shares only the
declared schema tables/defaults, as a receiver would. W2 uses the released SDK.
"""
import base64
import argparse
from collections import defaultdict
from dataclasses import asdict,fields
import gzip
import hashlib
import json
from pathlib import Path
import struct
import zlib
from saxil_core import SemanticFrame,VerbalUtt,Ent,Num,Date,Time,Cmp,VUnit,decode
from protocol.voice_extension import dicts as D
from json_controls import DEFAULTS,ENUMS,OPS,TYPES

ROOT=Path(__file__).resolve().parent

def logical(node):
    if isinstance(node,list):return [logical(x) for x in node]
    if isinstance(node,dict) and '_t' in node:
        cls=TYPES[node['_t']]
        kwargs={key:logical(value) for key,value in node.items() if key!='_t'}
        for key in ('known','units'):
            if key in kwargs:kwargs[key]=tuple(kwargs[key])
        return cls(**kwargs)
    return node

def read_unit(a):
    op=OPS[a[0]]
    values={}
    if op=='LEX':values={'w':D.LEX[a[1]] if isinstance(a[1],int) else a[1]}
    elif op=='NUM':values={'v':a[1],'unit':None if a[2] is None else D.CURRENCY[a[2]],'mode':D.NUM_MODE[a[3]]}
    elif op=='CUR':values={'unit':D.CURRENCY[a[1]]}
    elif op=='DATE':values=dict(zip(('y','mo','d'),a[1:]))
    elif op=='TIME':values=asdict(read_struct(Time,a[1]))
    elif op in ('NAME','EMPH'):values={'w':a[1]}
    elif op in ('ACR','PRON'):values={'w':a[1],'spoken':a[2]}
    elif op=='PAUSE':values={'pause':D.PAUSE[a[1]]}
    else:raise ValueError(op)
    return VUnit(op,**values)

def read_tagged(node):
    kind,payload=node
    if kind<8:return read_struct(TYPES[kind],payload)
    if kind==8:return [read_tagged(x) for x in payload]
    return payload

def read_struct(cls,body):
    names=[f.name for f in fields(cls)]
    result=dict(zip(names,DEFAULTS[cls]))
    for index,value in (body.items() if isinstance(body,dict) else enumerate(body)):
        name=names[int(index)]
        table=ENUMS.get((cls.__name__,name))
        if value is None:result[name]=None;continue
        if table is not None:value=table[value]
        elif cls is SemanticFrame:
            if name=='object':value=read_struct(Ent,value)
            elif name=='known':value=tuple(read_struct(Ent,x) for x in value)
            elif name=='cond':value=read_struct(Cmp,value)
            elif name=='time':value=read_struct((Date,Time)[value[0]],value[1])
            elif name=='attribute':value=read_tagged(value)
        elif cls is VerbalUtt and name=='units':value=tuple(read_unit(x) for x in value)
        elif cls is Cmp and name=='right' and isinstance(value,(dict,list)):value=read_struct(Num,value)
        result[name]=value
    return cls(**result)

def read_json(payload):
    node=json.loads(payload)
    if isinstance(node,dict):
        assert node['v']==2
        return logical(node['d'])
    assert node[0]==2 and node[1] in (0,1)
    return read_struct((SemanticFrame,VerbalUtt)[node[1]],node[2])

def decompress(packet):
    marker=packet[0]
    if marker==0:return packet[1:]
    if marker in (1,2):return zlib.decompress(packet[1:])
    if marker in (3,4):return gzip.decompress(packet[1:])
    raise ValueError(marker)

def candidate_sizes(payload):
    return [len(payload),len(zlib.compress(payload,1)),len(zlib.compress(payload,9)),
            len(gzip.compress(payload,compresslevel=1,mtime=0)),len(gzip.compress(payload,compresslevel=9,mtime=0))]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify-frozen',action='store_true',help='Portable audit of stored packets; no recompression or output writes')
    parser.add_argument('--out',default='independent_audit.json')
    args=parser.parse_args()
    out=ROOT/'results-v1'
    summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    seal=json.loads((ROOT/'SEAL.json').read_text(encoding='utf-8'))
    for name,digest in seal['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    corpus=[json.loads(line) for line in (ROOT/'corpus.jsonl').read_text(encoding='utf-8').splitlines()]
    raw=[json.loads(line) for line in (out/'raw_packets.jsonl').read_text(encoding='utf-8').splitlines()]
    measurement=[json.loads(line) for line in (out/'measurements.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(corpus)==len(raw)==len(measurement)==4608
    totals=defaultdict(lambda:[0,0,0])
    outcomes=defaultdict(lambda:[0,0,0])
    losses=[]
    payloads=defaultdict(list)
    for gold,packet,measured in zip(corpus,raw,measurement):
        assert gold['id']==packet['id']==measured['id']
        expected=asdict(logical(gold['ast']))
        wire=base64.b64decode(packet['w2_base64'],validate=True)
        docs={key:value.encode('utf-8') for key,value in packet['json'].items()}
        assert asdict(decode(wire))==expected
        for doc in docs.values():assert asdict(read_json(doc))==expected
        wp=base64.b64decode(packet['w2_adaptive_base64'],validate=True)
        jp=base64.b64decode(packet['json_adaptive_base64'],validate=True)
        assert decompress(wp)==wire and decompress(jp)==docs[packet['json_adaptive_representation']]
        if not args.verify_frozen:
            assert len(wp)==1+min(candidate_sizes(wire))
            assert len(jp)==1+min(n for d in docs.values() for n in candidate_sizes(d))
        w,j=len(wp)+4,len(jp)+4
        assert measured['adaptive_w2_framed_bytes']==w and measured['adaptive_json_framed_bytes']==j
        assert measured['raw_bytes']=={'w2':len(wire),**{k:len(v) for k,v in docs.items()}}
        kind='semantic' if isinstance(logical(gold['ast']),SemanticFrame) else 'verbal'
        for group in ('all',kind,gold['family'],str(gold['seed'])):
            totals[group][0]+=1;totals[group][1]+=w;totals[group][2]+=j
            outcomes[group][0]+=w<j;outcomes[group][1]+=w>j;outcomes[group][2]+=w==j
        if w>=j:losses.append({'id':gold['id'],'family':gold['family'],'w2_bytes':w,'json_bytes':j})
        payloads['w2'].append(wire)
        for key,doc in docs.items():payloads[key].append(doc)
    for name,observed in totals.items():
        ref=summary['all_messages'] if name=='all' else summary['primary_groups'].get(name,summary['by_family'].get(name,summary['by_seed'].get(name)))
        assert ref and observed==[ref['n'],ref['w2_framed_bytes'],ref['best_json_framed_bytes']]
        assert abs(ref['w2_reduction_fraction']-(1-observed[1]/observed[2]))<1e-12
        assert outcomes[name]==[ref['w2_smaller_cases'],ref['json_smaller_cases'],ref['ties']]
        if 'predeclared_20pct_gate_passed' in ref:assert ref['predeclared_20pct_gate_passed']==(1-observed[1]/observed[2]>=.2)
    # Rebuild each compressed batch from raw payloads; no stored lengths trusted.
    for batch in summary['batch_compression']:
        assert sum(row['n'] for row in batch['details'])==4608
        assert sum(row['w2_bytes'] for row in batch['details'])==batch['w2_bytes']
        assert sum(row['json_bytes'] for row in batch['details'])==batch['best_json_bytes']
        assert abs(batch['w2_reduction_fraction']-(1-batch['w2_bytes']/batch['best_json_bytes']))<1e-12
        if args.verify_frozen:continue
        ws=js=0
        for start in range(0,4608,batch['batch_size']):
            stop=min(start+batch['batch_size'],4608)
            blobs={key:b''.join(struct.pack('!I',len(p))+p for p in values[start:stop]) for key,values in payloads.items()}
            blobs['shortest_json']=b''.join(struct.pack('!I',len(p))+p for i in range(start,stop) for p in [min((payloads[k][i] for k in payloads if k!='w2'),key=len)])
            ws+=5+min(candidate_sizes(blobs['w2']))
            js+=5+min(size for key,blob in blobs.items() if key!='w2' for size in candidate_sizes(blob))
        assert ws==batch['w2_bytes'] and js==batch['best_json_bytes']
    result={'status':'SECOND_PASS_AUDIT_PASSED','records':4608,'semantic_decoder':'separate JSON decoder; published W2 SDK',
            'all_field_differences':0,'size_or_compression_discrepancies':0,'seal_valid':True,
            'primary_totals':{k:totals[k] for k in ('semantic','verbal','all')},'w2_ties_or_losses':losses,
            'result_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}}
    if args.verify_frozen:
        original=json.loads((out/'independent_audit.json').read_text(encoding='utf-8'))
        for name,digest in original['result_files_sha256'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
        print(json.dumps({'status':'PORTABLE_FROZEN_PACKET_AUDIT_PASSED','records':4608,'all_field_differences':0,'size_discrepancies':0,'seal_valid':True,'note':'Original compressed packet sizes verified; no cross-version recompression equivalence assumed'}))
        return
    target=out/args.out
    if target.parent!=out or target.suffix!='.json':raise ValueError('new JSON output name required')
    if target.exists():raise RuntimeError('Audit already exists')
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
