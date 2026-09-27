"""Inspect fixed public PR ZIP directory via validated HTTP ranges, no full download."""
import io
import json
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone

from project_paths import PROJECT

REVISION='63aa4abe7dd7217d9b0b108894c7d893e2b29aef'
FILES={'20210517':14040008257,'20210524':11721862708,'20211203':18012496133,'20220606':9859441848}


class RangeReader(io.RawIOBase):
    def __init__(self,url,size):
        self.url,self.size,self.position=url,size,0
        self.requests=[]
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        if self.position<0: raise ValueError('Negative ZIP seek')
        return self.position
    def read(self,n=-1):
        n=min(self.size-self.position,n if n>=0 else self.size-self.position)
        if n<=0:return b''
        if n>8*1024*1024: raise ValueError('Refusing oversized range request')
        start,end=self.position,self.position+n-1
        # Distinct query prevents an intermediate cache serving a different byte range.
        url=self.url+f'?d01range={start}-{end}'
        request=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
        with urllib.request.urlopen(request,timeout=45) as response:
            expected=f'bytes {start}-{end}/{self.size}'
            if response.status!=206 or response.headers.get('Content-Range')!=expected:
                raise RuntimeError('Range not honored; full download refused')
            data=response.read(n+1)
        if len(data)!=n:raise RuntimeError('Incomplete range')
        self.requests.append({'start':start,'end':end,'bytes':len(data)})
        self.position+=n
        return data


def main():
    report={'checked_utc':datetime.now(timezone.utc).isoformat(),'revision':REVISION,'full_archive_sha256_verified':False,
            'method':'fixed public URL, exact HTTP 206 Content-Range and length checks; ZIP central directory only', 'cases':[]}
    for day,size in FILES.items():
        url=f'https://huggingface.co/datasets/Lemma-RCA-NEC/Product_Review_Original/resolve/{REVISION}/{day}.zip'
        reader=RangeReader(url,size)
        with zipfile.ZipFile(reader) as archive:
            entries=[{'member':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':f'{i.CRC:08x}'} for i in archive.infolist() if not i.is_dir()]
        case={'day':day,'url':url,'archive_bytes':size,'entries':entries,'requests':reader.requests,
              'first_level_counts':dict(Counter('/'.join(i['member'].split('/')[:3]) for i in entries))}
        report['cases'].append(case)
        print(json.dumps({'day':day,'files':len(entries),'downloaded_bytes':sum(r['bytes'] for r in reader.requests),
                          'log_examples':[i for i in entries if 'log' in i['member'].lower()][:4]},ensure_ascii=False),flush=True)
    output=PROJECT/'docs/evidence/d01_pr_original_remote_index.json'
    if output.exists():raise FileExistsError(output)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(str(output),flush=True)


if __name__=='__main__':main()
