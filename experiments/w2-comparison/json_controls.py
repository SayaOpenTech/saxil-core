"""Independent lossless JSON AST encodings with shared schemas and defaults.

Numeric enum IDs and sparse omission deliberately give JSON the same static
domain knowledge as W2. These are benchmark schemas, not public SDK APIs.
"""
from dataclasses import asdict, fields, is_dataclass
import json
from saxil_core import SemanticFrame, VerbalUtt, VUnit, Ent, Num, Date, Time, Cmp
from protocol.voice_extension import dicts as D

TYPES=(SemanticFrame,VerbalUtt,Ent,Num,Date,Time,Cmp,VUnit)
OPS=('LEX','NUM','CUR','DATE','TIME','NAME','ACR','PRON','PAUSE','EMPH')
DEFAULTS={SemanticFrame:['user','ask','query_price','pos',None,None,None,None,None,None,None,None,(),None,None],
          VerbalUtt:['statement',()],Ent:[1,'product',None,None],Num:[0,None],Date:[0,0,0],
          Time:[None]*6,Cmp:['eq','',0],VUnit:['LEX']+[None]*(len(fields(VUnit))-1)}
ENUMS={('SemanticFrame','speaker'):D.SPEAKER,('SemanticFrame','act'):D.ACT,
       ('SemanticFrame','intent'):D.INTENT,('SemanticFrame','polarity'):D.POLARITY,
       ('SemanticFrame','action'):D.ACTION,('SemanticFrame','affect'):D.AFFECT,
       ('SemanticFrame','qtype'):D.QTYPE,('SemanticFrame','request'):D.REQUEST,
       ('Ent','typ'):D.ENT_TYPE,('Ent','ref'):D.REF,('Num','unit'):D.CURRENCY,
       ('Time','rel'):D.REL,('Time','weekday'):D.WEEKDAY,('Time','unit'):D.DUR_UNIT,
       ('Cmp','op'):D.CMP_OP,('VerbalUtt','utt_type'):D.UTT_TYPE}

def dumps(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode('utf-8')

def unit_pack(u):
    op=OPS.index(u.op)
    if u.op=='LEX':
        return [op,D.LEX.index(u.w) if u.w in D.LEX else u.w]
    if u.op=='NUM':
        return [op,u.v,None if u.unit is None else D.CURRENCY.index(u.unit),D.NUM_MODE.index(u.mode)]
    if u.op=='CUR': return [op,D.CURRENCY.index(u.unit)]
    if u.op=='DATE': return [op,u.y,u.mo,u.d]
    if u.op=='TIME': return [op,pack(Time(h=u.h,m=u.m,rel=u.rel,weekday=u.weekday,unit=u.unit,v=u.v),False)]
    if u.op in ('NAME','EMPH'): return [op,u.w]
    if u.op in ('ACR','PRON'): return [op,u.w,u.spoken]
    if u.op=='PAUSE': return [op,D.PAUSE.index(u.pause)]
    raise ValueError(u.op)

def unit_unpack(a):
    op=OPS[a[0]]
    if op=='LEX':return VUnit(op,w=D.LEX[a[1]] if isinstance(a[1],int) else a[1])
    if op=='NUM':return VUnit(op,v=a[1],unit=None if a[2] is None else D.CURRENCY[a[2]],mode=D.NUM_MODE[a[3]])
    if op=='CUR':return VUnit(op,unit=D.CURRENCY[a[1]])
    if op=='DATE':return VUnit(op,y=a[1],mo=a[2],d=a[3])
    if op=='TIME':return VUnit(op,**asdict(unpack(Time,a[1])))
    if op in ('NAME','EMPH'):return VUnit(op,w=a[1])
    if op in ('ACR','PRON'):return VUnit(op,w=a[1],spoken=a[2])
    if op=='PAUSE':return VUnit(op,pause=D.PAUSE[a[1]])
    raise ValueError(op)

def encode_field(cls,name,value,sparse):
    table=ENUMS.get((cls.__name__,name))
    if value is None:return None
    if table is not None:return table.index(value)
    if cls is SemanticFrame:
        if name=='object':return pack(value,sparse)
        if name=='known':return [pack(v,sparse) for v in value]
        if name=='cond':return pack(value,sparse)
        if name=='time':return [0 if isinstance(value,Date) else 1,pack(value,sparse)]
        if name=='attribute':return tagged(value,sparse)
    if cls is VerbalUtt and name=='units':return [unit_pack(v) for v in value]
    if cls is Cmp and name=='right':return pack(value,sparse) if isinstance(value,Num) else value
    return value

def decode_field(cls,name,value):
    if value is None:return None
    table=ENUMS.get((cls.__name__,name))
    if table is not None:return table[value]
    if cls is SemanticFrame:
        if name=='object':return unpack(Ent,value)
        if name=='known':return tuple(unpack(Ent,v) for v in value)
        if name=='cond':return unpack(Cmp,value)
        if name=='time':return unpack(Date if value[0]==0 else Time,value[1])
        if name=='attribute':return untagged(value)
    if cls is VerbalUtt and name=='units':return tuple(unit_unpack(v) for v in value)
    if cls is Cmp and name=='right':return unpack(Num,value) if isinstance(value,(list,dict)) else value
    return value

def tagged(value,sparse):
    if is_dataclass(value):return [TYPES.index(type(value)),pack(value,sparse)]
    if isinstance(value,list):return [8,[tagged(v,sparse) for v in value]]
    return [9,value]

def untagged(value):
    tag,data=value
    if tag<8:return unpack(TYPES[tag],data)
    if tag==8:return [untagged(v) for v in data]
    return data

def pack(obj,sparse):
    cls=type(obj)
    fs=fields(obj)
    defaults=DEFAULTS[cls]
    assert len(defaults)==len(fs),(cls,len(defaults),len(fs))
    values=[encode_field(cls,f.name,getattr(obj,f.name),sparse) for f in fs]
    dense=values[:]
    while dense and getattr(obj,fs[len(dense)-1].name)==defaults[len(dense)-1]:dense.pop()
    if not sparse:return dense
    sparse_values={str(i):v for i,v in enumerate(values) if getattr(obj,fs[i].name)!=defaults[i]}
    return sparse_values if len(dumps(sparse_values))<len(dumps(dense)) else dense

def unpack(cls,body):
    fs=fields(cls)
    values=DEFAULTS[cls][:]
    pairs=body.items() if isinstance(body,dict) else enumerate(body)
    for key,value in pairs:
        index=int(key)
        values[index]=decode_field(cls,fs[index].name,value)
    return cls(**{f.name:v for f,v in zip(fs,values)})

def positional_encode(obj):
    return dumps([2,0 if isinstance(obj,SemanticFrame) else 1,pack(obj,False)])

def adaptive_encode(obj):
    return dumps([2,0 if isinstance(obj,SemanticFrame) else 1,pack(obj,True)])

def compact_decode(payload):
    version,kind,body=json.loads(payload)
    if version!=2 or kind not in (0,1):raise ValueError('schema')
    return unpack(SemanticFrame if kind==0 else VerbalUtt,body)

def named_node(value):
    if is_dataclass(value):
        return {'_t':TYPES.index(type(value)),**{f.name:named_node(getattr(value,f.name)) for f in fields(value) if getattr(value,f.name) not in (None,())}}
    if isinstance(value,(tuple,list)):return [named_node(v) for v in value]
    return value

def named_restore(value):
    if isinstance(value,list):return [named_restore(v) for v in value]
    if isinstance(value,dict) and '_t' in value:
        cls=TYPES[value['_t']]
        kwargs={k:named_restore(v) for k,v in value.items() if k!='_t'}
        if cls is VerbalUtt:kwargs['units']=tuple(kwargs['units'])
        if cls is SemanticFrame and 'known' in kwargs:kwargs['known']=tuple(kwargs['known'])
        return cls(**kwargs)
    return value

def named_encode(obj):return dumps({'v':2,'d':named_node(obj)})
def named_decode(payload):
    data=json.loads(payload)
    if data['v']!=2:raise ValueError('schema')
    return named_restore(data['d'])
