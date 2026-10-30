"""Build all preregistered synthetic cases; fail rather than drop bad cases."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import string
from saxil_core import SemanticFrame as S, VerbalUtt as U, VUnit as V, Ent, Num, Date, Time, Cmp, encode, decode
from protocol.voice_extension import dicts as D
from json_controls import named_node,named_restore,named_encode,named_decode,positional_encode,adaptive_encode,compact_decode

ROOT=Path(__file__).resolve().parent

def name(r):return 'کالا-'+''.join(r.choices(string.ascii_letters+string.digits,k=r.randint(4,20)))
def eid(r):return r.choice([1,2,63,127,128,254,255])
def price(r):return r.randrange(1,2**32)

def make(f,r,i):
    if f=='minimal_semantic':return S(r.choice(D.SPEAKER),r.choice(D.ACT),r.choice(D.INTENT),r.choice(D.POLARITY))
    if f=='entity_query':return S('user','ask','query_price','pos',action='query',object=Ent(eid(r),'product',r.choice(D.REF[1:])))
    if f=='literal_names':return S('agent','assert','query_name','pos',object=Ent(eid(r),'person',name=name(r)))
    if f=='price_frame':return S('agent','assert','state_price','pos',action='state',object=Ent(eid(r),'product','this'),attribute=Num(price(r),'toman'))
    if f=='digit_string_frame':return S('agent','assert','state_order_id','pos',attribute=Num(f'{r.randrange(10**15):016d}',None))
    if f=='condition_frame':return S('user','request','notify_if','pos',action='notify',object=Ent(eid(r),'product','this'),cond=Cmp(r.choice(D.CMP_OP),'price',Num(price(r),'toman')),time=Time(unit='minute',v=r.randrange(1,1000)))
    if f=='time_date':return S('user','request','schedule','pos',action='schedule',time=Date(r.randrange(2000,2100),r.randrange(1,13),r.randrange(1,29)) if i%2 else Time(h=r.randrange(24),m=r.randrange(60)))
    if f=='known_entities':return S('user','ask','query_company','pos',object=Ent(eid(r),'company','this'),known=tuple(Ent(j+1,'person',name=name(r)) for j in range(r.randrange(1,9))))
    if f=='verbal_lex':return U(r.choice(D.UTT_TYPE),tuple(V('LEX',w=r.choice(D.LEX)) for _ in range(r.choice([4,8,16,32]))))
    if f=='verbal_numbers':return U('statement',(V('LEX',w='قیمت'),V('NUM',v=price(r),unit='toman',mode='cardinal'),V('NUM',v='0'+str(r.randrange(10**9,10**10)),mode='phone')))
    if f=='verbal_literals':return U('statement',(V('NAME',w=name(r)),V('ACR',w='API'+str(r.randrange(10000)),spoken='ای پی آی'),V('PRON',w=name(r),spoken='تلفظ ساختگی')))
    if f=='mixed_verbal':return U('statement',(V('LEX',w='سفارش'),V('NUM',v=price(r),mode='digit_groups'),V('CUR',unit='toman'),V('DATE',y=2026,mo=r.randrange(1,13),d=r.randrange(1,29)),V('TIME',h=r.randrange(24),m=r.randrange(60)),V('PAUSE',pause=r.choice(D.PAUSE)),V('EMPH',w='تأیید')))
    raise ValueError(f)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    protocol=json.loads((ROOT/'PRE_REGISTERED_PROTOCOL.json').read_text(encoding='utf-8'))
    corpus=ROOT/'corpus.jsonl'
    seal=ROOT/'SEAL.json'
    if corpus.exists() or seal.exists():raise SystemExit('Refuse to replace frozen corpus/seal')
    rows=[]
    for seed in protocol['seeds']:
        rng=random.Random(seed)
        for family in protocol['families']:
            for i in range(protocol['cases_per_family_per_seed']):
                obj=make(family,rng,i)
                # Constructive correctness checks only; do not inspect size/timing.
                expected=asdict(obj)
                for restored in (decode(encode(obj)),named_decode(named_encode(obj)),compact_decode(positional_encode(obj)),compact_decode(adaptive_encode(obj))):
                    if asdict(restored)!=expected:raise ValueError(('semantic mismatch',seed,family,i,expected,asdict(restored)))
                rows.append({'id':f'{seed}-{family}-{i:03d}','seed':seed,'family':family,'ast':named_node(obj)})
    assert len(rows)==protocol['total_records'] and len({x['id'] for x in rows})==len(rows)
    random.Random(20261030).shuffle(rows)
    corpus.write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in rows),encoding='utf-8')
    files=['PRE_REGISTERED_PROTOCOL.json','json_controls.py','build_corpus.py','run_study.py','corpus.jsonl']
    seal.write_text(json.dumps({'phase':'FROZEN_BEFORE_SIZE_AND_TIMING_MEASUREMENT','records':len(rows),'files':{f:sha(ROOT/f) for f in files}},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'records':len(rows),'all_fields_equivalence_passed':True,'seal_written':True}))

if __name__=='__main__':main()
