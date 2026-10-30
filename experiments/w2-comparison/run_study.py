"""Run the sealed CPU-only W2/strong-JSON engineering comparison."""
from __future__ import annotations
import argparse
import base64
from collections import defaultdict
from dataclasses import asdict
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import statistics
import struct
import sysconfig
import time
import zlib
import saxil_core
from saxil_core import encode,decode
from json_controls import named_restore,named_encode,named_decode,positional_encode,adaptive_encode,compact_decode

ROOT=Path(__file__).resolve().parent
COMPRESSORS=(lambda b:b,lambda b:zlib.compress(b,1),lambda b:zlib.compress(b,9),
             lambda b:gzip.compress(b,compresslevel=1,mtime=0),lambda b:gzip.compress(b,compresslevel=9,mtime=0))
CODEC_NAMES=('raw','zlib1','zlib9','gzip1','gzip9')
ENCODERS={'w2':encode,'json_named':named_encode,'json_dense':positional_encode,'json_adaptive':adaptive_encode}
DECODERS={'w2':decode,'json_named':named_decode,'json_dense':compact_decode,'json_adaptive':compact_decode}

def check_seal():
    seal=json.loads((ROOT/'SEAL.json').read_text(encoding='utf-8'))
    for name,digest in seal['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Seal mismatch: '+name)
    return seal

def b64(data):return base64.b64encode(data).decode('ascii')

def best_packet(payloads):
    choices=[(len(data),name,index,data) for name,payload in payloads.items()
             for index,fn in enumerate(COMPRESSORS) for data in (fn(payload),)]
    _,name,index,data=min(choices,key=lambda x:(x[0],x[1],x[2]))
    return bytes([index])+data,name,CODEC_NAMES[index]

def unpack_packet(packet):
    index,body=packet[0],packet[1:]
    if index in (1,2):return zlib.decompress(body)
    if index in (3,4):return gzip.decompress(body)
    if index==0:return body
    raise ValueError('bad codec')

def frame(data):return struct.pack('!I',len(data))+data

def byte_summary(rows):
    w=sum(r['adaptive_w2_framed_bytes'] for r in rows)
    j=sum(r['adaptive_json_framed_bytes'] for r in rows)
    return {'n':len(rows),'w2_framed_bytes':w,'best_json_framed_bytes':j,
            'w2_reduction_fraction':1-w/j,'w2_smaller_cases':sum(r['adaptive_w2_framed_bytes']<r['adaptive_json_framed_bytes'] for r in rows),
            'json_smaller_cases':sum(r['adaptive_w2_framed_bytes']>r['adaptive_json_framed_bytes'] for r in rows),
            'ties':sum(r['adaptive_w2_framed_bytes']==r['adaptive_json_framed_bytes'] for r in rows)}

def measure(rows,objects,packets,protocol):
    keys=list(ENCODERS)
    trials=defaultdict(list)
    for _ in range(protocol['timing']['warmup_passes']):
        for key in keys:
            for obj in objects:ENCODERS[key](obj)
            for packet in packets[key]:DECODERS[key](packet)
    for trial in range(protocol['timing']['trials']):
        order=keys[trial%len(keys):]+keys[:trial%len(keys)]
        for key in order:
            start=time.perf_counter_ns()
            for obj in objects:ENCODERS[key](obj)
            trials[key+'_encode'].append((time.perf_counter_ns()-start)/len(objects))
            start=time.perf_counter_ns()
            for packet in packets[key]:DECODERS[key](packet)
            trials[key+'_decode'].append((time.perf_counter_ns()-start)/len(objects))
    return {key:{'ns_per_ast_trial':value,'median_ns_per_ast':statistics.median(value)} for key,value in trials.items()}

def batched(rows,packets,size):
    totals={'w2':0,'json':0}
    detail=[]
    for start in range(0,len(rows),size):
        end=min(start+size,len(rows))
        wbody=b''.join(frame(p) for p in packets['w2'][start:end])
        json_alternatives={key:b''.join(frame(p) for p in packets[key][start:end]) for key in ENCODERS if key!='w2'}
        json_alternatives['json_per_message_shortest']=b''.join(frame(min((packets[k][i] for k in ENCODERS if k!='w2'),key=len)) for i in range(start,end))
        wp,_,wc=best_packet({'w2':wbody})
        jp,jname,jc=best_packet(json_alternatives)
        # Check the selected compressed batch preserves every original frame.
        if unpack_packet(wp)!=wbody or unpack_packet(jp)!=json_alternatives[jname]:raise AssertionError('batch compression')
        wbytes,jbytes=len(frame(wp)),len(frame(jp))
        totals['w2']+=wbytes;totals['json']+=jbytes
        detail.append({'start':start,'n':end-start,'w2_bytes':wbytes,'json_bytes':jbytes,'w2_codec':wc,'json_codec':jc,'json_representation':jname})
    return {'batch_size':size,'n':len(rows),'batches':len(detail),'w2_bytes':totals['w2'],'best_json_bytes':totals['json'],
            'w2_reduction_fraction':1-totals['w2']/totals['json'],'details':detail}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='results-v1')
    args=parser.parse_args()
    out=(ROOT/args.out).resolve()
    if out.parent!=ROOT or out.exists():raise RuntimeError('Output must be a new immediate child directory')
    if version('saxil-core')!='0.1.0' or not Path(saxil_core.__file__).resolve().is_relative_to(Path(sysconfig.get_path('purelib')).resolve()):
        raise RuntimeError('Use the verified installed released wheel')
    seal=check_seal()
    protocol=json.loads((ROOT/'PRE_REGISTERED_PROTOCOL.json').read_text(encoding='utf-8'))
    source_rows=[json.loads(line) for line in (ROOT/'corpus.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(source_rows)==protocol['total_records']
    objects=[named_restore(row['ast']) for row in source_rows]
    packets={key:[] for key in ENCODERS}
    rows=[]
    raw=[]
    start=time.perf_counter()
    for index,(record,obj) in enumerate(zip(source_rows,objects)):
        encoded={key:fn(obj) for key,fn in ENCODERS.items()}
        expected=asdict(obj)
        for key,data in encoded.items():
            restored=DECODERS[key](data)
            if asdict(restored)!=expected or ENCODERS[key](restored)!=data:raise AssertionError(('equivalence/canonical',record['id'],key))
            packets[key].append(data)
        wp,_,wc=best_packet({'w2':encoded['w2']})
        jp,jname,jc=best_packet({k:v for k,v in encoded.items() if k!='w2'})
        if asdict(decode(unpack_packet(wp)))!=expected or asdict(DECODERS[jname](unpack_packet(jp)))!=expected:raise AssertionError('adaptive equivalence')
        rows.append({'id':record['id'],'family':record['family'],'seed':record['seed'],
                     'raw_bytes':{k:len(v) for k,v in encoded.items()},
                     'adaptive_w2_framed_bytes':len(wp)+4,'adaptive_json_framed_bytes':len(jp)+4,
                     'w2_codec':wc,'json_codec':jc,'json_representation':jname})
        raw.append({'id':record['id'],'w2_base64':b64(encoded['w2']),
                    'json':{k:v.decode('utf-8') for k,v in encoded.items() if k!='w2'},
                    'w2_adaptive_base64':b64(wp),'json_adaptive_base64':b64(jp),'json_adaptive_representation':jname})
        if (index+1)%512==0:print(f'Validated/measured {index+1}/{len(objects)}',flush=True)
    timing=measure(rows,objects,packets,protocol)
    by_family={family:byte_summary([r for r in rows if r['family']==family]) for family in protocol['families']}
    groups={kind:byte_summary([r for r in rows if r['family'].startswith(('verbal_','mixed_'))==(kind=='verbal')]) for kind in ('semantic','verbal')}
    for kind in groups:groups[kind]['predeclared_20pct_gate_passed']=groups[kind]['w2_reduction_fraction']>=.2
    batch_results=[batched(rows,packets,n) for n in (128,len(rows))]
    # Also quantify JSON-only transports: actual base64(JSON string) carrier size.
    json_only_carrier=sum(len(json.dumps(base64.b64encode(p).decode('ascii'),separators=(',',':')).encode('utf-8'))+4 for p in packets['w2'])
    result={'study':protocol['study'],'status':'COMPLETE','semantic_equivalence_records':len(rows),
            'failed_or_dropped_records':0,'sdk_version':version('saxil-core'),
            'environment':{'python':platform.python_version(),'implementation':platform.python_implementation(),'os':platform.system(),'machine':platform.machine()},
            'all_messages':byte_summary(rows),'primary_groups':groups,'by_family':by_family,
            'by_seed':{str(seed):byte_summary([r for r in rows if r['seed']==seed]) for seed in protocol['seeds']},
            'raw_totals':{key:sum(map(len,value)) for key,value in packets.items()},
            'batch_compression':batch_results,'timing':timing,
            'json_only_transport':{'w2_base64_json_string_plus_4byte_frame':json_only_carrier,
                                   'best_raw_json_plus_4byte_frame':sum(min(len(packets[k][i]) for k in ENCODERS if k!='w2')+4 for i in range(len(rows)))},
            'seals':seal,'elapsed_seconds':time.perf_counter()-start,
            'limits':['Synthetic balanced supported AST coverage, not a production distribution','Compression and shared dictionaries are allowed equally','No neural model, semantic extraction, LLM token or voice latency result','JSON codec validation work differs; timings are descriptive, not a validation-quality comparison','Payload and four-byte application framing only; no HTTP/TLS/IP measurements']}
    check_seal()
    out.mkdir()
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'measurements.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
    (out/'raw_packets.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in raw),encoding='utf-8')
    print(json.dumps({'status':'COMPLETE','n':len(rows),'primary_groups':groups,'all_messages':result['all_messages'],'batch_sizes':[{k:v for k,v in x.items() if k!='details'} for x in batch_results]},indent=2))

if __name__=='__main__':main()
