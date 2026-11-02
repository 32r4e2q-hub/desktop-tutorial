"""Deterministic framing and printed-portrait corrections, not new image generation."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageOps,ImageFilter,ImageDraw
HERE=Path(__file__).resolve().parent
REF=HERE/'reference'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if (REF/'composite-repairs.json').exists():
        raise RuntimeError('Already corrected; refusing a destructive second crop')
    audit=[]
    for role,box in [('C08',(20,0,844,835)),('C03B',(55,0,809,825))]:
        path=REF/f'{role}_face.png'
        before=sha(path)
        with Image.open(path) as im:im.crop(box).save(path)
        audit.append(dict(id=role+'_face',method='crop generated image to head and collar; no synthesis or stretching',crop=list(box),before_sha256=before,sha256=sha(path)))
    path=REF/'P02.png';before=sha(path)
    paper=Image.open(path).convert('RGB')
    def imprint(source,box,quad):
        face=Image.open(REF/source).convert('RGB').crop(box).resize((240,300),Image.Resampling.LANCZOS)
        grey=ImageOps.autocontrast(ImageOps.grayscale(face))
        edges=ImageOps.invert(grey.filter(ImageFilter.FIND_EDGES))
        grey=Image.blend(edges,grey,.5)
        grey=ImageOps.posterize(grey.convert('RGB'),3).convert('L')
        ink=ImageOps.colorize(grey,'#483b2a','#e5d0aa')
        # PIL perspective coefficients map destination paper pixels to source portrait pixels.
        mat=[];rhs=[]
        for (x,y),(u,v) in zip(quad,[(0,0),(239,0),(239,299),(0,299)]):
            mat.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]])
            rhs.extend([u,v])
        coeff=np.linalg.solve(np.array(mat,dtype=float),np.array(rhs,dtype=float))
        warped=ink.transform(paper.size,Image.Transform.PERSPECTIVE,tuple(coeff),Image.Resampling.BICUBIC)
        mask=Image.new('L',paper.size);ImageDraw.Draw(mask).polygon(quad,fill=255)
        paper.paste(warped,(0,0),mask)
    imprint('C01_face.png',(400,0,1000,768),[(394,223),(518,243),(442,357),(308,332)])
    imprint('C03_face.png',(60,0,804,1020),[(547,251),(668,264),(600,380),(470,363)])
    paper.save(path)
    audit.append(dict(id='P02',method='perspective-mapped duotone ink portraits from actual character face references; newspaper base retained',inputs={x:sha(REF/x) for x in ['C01_face.png','C03_face.png']},before_sha256=before,sha256=sha(path)))
    (REF/'composite-repairs.json').write_text(json.dumps({'note':'One-time correction of outputs from run 41472228725. Do not re-run on already corrected files.','items':audit},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
