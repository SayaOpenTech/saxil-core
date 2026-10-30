"""Separate-process TCP validation of actual frozen W2 and JSON packets."""
import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time
from saxil_core import decode
from audit_results import logical,read_json,decompress

ROOT=Path(__file__).resolve().parent

def digest(obj):return hashlib.sha256(json.dumps(asdict(obj),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).digest()

def read_exact(sock,n):
    chunks=[]
    while n:
        chunk=sock.recv(n)
        if not chunk:raise EOFError('truncated stream')
        chunks.append(chunk);n-=len(chunk)
    return b''.join(chunks)

def receiver(arm,folder):
    count=received=sent=0
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(10)
        ready=folder/'ready.json'
        tmp=folder/'ready.json.tmp'
        tmp.write_text(json.dumps({'port':server.getsockname()[1]}),encoding='utf-8');tmp.replace(ready)
        conn,_=server.accept()
        with conn:
            conn.settimeout(10)
            while True:
                header=read_exact(conn,4);received+=4
                length=struct.unpack('!I',header)[0]
                if length==0:break
                if length>64000:raise ValueError('oversized packet')
                packet=read_exact(conn,length);received+=length
                body=decompress(packet)
                obj=decode(body) if arm=='w2' else read_json(body)
                conn.sendall(digest(obj));sent+=32;count+=1
    (folder/'receiver.json').write_text(json.dumps({'arm':arm,'decoded_messages':count,'actual_received_application_bytes':received,'actual_sent_digest_bytes':sent}),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--receiver',choices=('w2','json'))
    parser.add_argument('--folder')
    parser.add_argument('--out',default='transport-v1',help='New output directory name under results-v1')
    args=parser.parse_args()
    if args.receiver:
        receiver(args.receiver,Path(args.folder));return
    root=(ROOT/'results-v1'/args.out).resolve()
    if root.parent!=(ROOT/'results-v1').resolve():raise ValueError('new local output directory name required')
    if root.exists():raise RuntimeError('Refuse overwrite')
    root.mkdir()
    corpus=[json.loads(line) for line in (ROOT/'corpus.jsonl').read_text(encoding='utf-8').splitlines()]
    packets=[json.loads(line) for line in (ROOT/'results-v1/raw_packets.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(corpus)==len(packets)==4608
    expected=[digest(logical(row['ast'])) for row in corpus]
    report={}
    for arm in ('w2','json'):
        folder=root/arm;folder.mkdir()
        process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--receiver',arm,'--folder',str(folder)],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            deadline=time.monotonic()+10
            while not (folder/'ready.json').exists():
                if process.poll() is not None:raise RuntimeError(process.communicate()[1].decode('utf-8','replace'))
                if time.monotonic()>deadline:raise TimeoutError('receiver startup')
                time.sleep(.02)
            port=json.loads((folder/'ready.json').read_text(encoding='utf-8'))['port']
            transmitted=0
            with socket.create_connection(('127.0.0.1',port),timeout=10) as client:
                for i,(row,expected_digest) in enumerate(zip(packets,expected)):
                    payload=base64.b64decode(row[arm+'_adaptive_base64'],validate=True)
                    framed=struct.pack('!I',len(payload))+payload
                    client.sendall(framed);transmitted+=len(framed)
                    if read_exact(client,32)!=expected_digest:raise AssertionError(('all-field digest',arm,i))
                client.sendall(b'\0\0\0\0');transmitted+=4
            stdout,stderr=process.communicate(timeout=20)
            if process.returncode:raise RuntimeError(stderr.decode('utf-8','replace'))
            data=json.loads((folder/'receiver.json').read_text(encoding='utf-8'))
            assert data['decoded_messages']==4608 and data['actual_received_application_bytes']==transmitted
            report[arm]={**data,'sender_checked_ast_digests':4608,'all_field_or_order_discrepancies':0}
        finally:
            if process.poll() is None:process.kill();process.communicate()
    w=report['w2']['actual_received_application_bytes'];j=report['json']['actual_received_application_bytes']
    report.update(status='ACTUAL_TCP_TRANSFER_VALIDATED',forward_application_byte_reduction=1-w/j,
                  scope='Separate receiver process; application bytes including termination frame; no TCP/IP/TLS or latency claim')
    (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
