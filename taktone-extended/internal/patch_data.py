"""Python-only patch recipe: stock-source copies and compressed replacement bytes."""
import base64
import hashlib
import json
import zlib

def sha(data):
    return hashlib.sha256(data).hexdigest()

def literal(data):
    return {'data': base64.b64encode(zlib.compress(data,9)).decode('ascii'), 'bytes': len(data)}

def relative(source,original,target):
    """Copy unchanged stock runs; store only replacement runs."""
    ops=[];i=0
    while i<len(target):
        equal=i<len(original) and target[i]==original[i]
        end=i+1
        while end<len(target) and (end<len(original) and target[end]==original[end])==equal:
            end+=1
        ops.append({'copy':source,'offset':i,'bytes':end-i} if equal else literal(target[i:end]))
        i=end
    return ops

def create(dt,dn,image,version):
    sources={'digitakt:3':dt.section(3),'digitone:6':dn.section(6),'digitone:7':dn.section(7)}
    original=sources['digitakt:3']
    ops=relative('digitakt:3',original,image[:len(original)])
    cursor=len(original)
    embedded=[]
    for name in ('digitone:6','digitone:7'):
        stock=sources[name]
        # Section 6's second byte is adjusted by the serial framing adapter.
        skip=2 if name.endswith(':6') else 0
        at=image.find(stock[skip:skip+64],cursor)
        if at>=0:
            at-=skip
            embedded.append((at,name,stock))
    for at,name,stock in sorted(embedded):
        if at<cursor:raise ValueError('Overlapping embedded stock sections')
        if at>cursor:ops.append(literal(image[cursor:at]))
        ops+=relative(name,stock,image[at:at+len(stock)])
        cursor=at+len(stock)
    if cursor<len(image):ops.append(literal(image[cursor:]))
    result=dict(format=1,version=version,image_bytes=len(image),image_sha256=sha(image),
                source_sha256={name:sha(data) for name,data in sources.items()},ops=ops)
    if apply(result,dt,dn)!=image:raise ValueError('Patch recipe round trip differs')
    return result

def apply(recipe,dt,dn):
    if recipe['format']!=1:raise ValueError('Unsupported patch recipe format')
    sources={'digitakt:3':dt.section(3),'digitone:6':dn.section(6),'digitone:7':dn.section(7)}
    for name,digest in recipe['source_sha256'].items():
        if sha(sources[name])!=digest:raise ValueError('Stock section hash differs: '+name)
    parts=[]
    for op in recipe['ops']:
        if 'copy' in op:
            source=sources[op['copy']];start=op['offset'];end=start+op['bytes']
            if start<0 or end>len(source):raise ValueError('Stock copy outside source bounds')
            block=source[start:end]
        else:block=zlib.decompress(base64.b64decode(op['data'],validate=True))
        if len(block)!=op['bytes']:raise ValueError('Patch block length differs')
        parts.append(block)
    image=b''.join(parts)
    if len(image)!=recipe['image_bytes'] or sha(image)!=recipe['image_sha256']:
        raise ValueError('Reconstructed application hash differs')
    return image
