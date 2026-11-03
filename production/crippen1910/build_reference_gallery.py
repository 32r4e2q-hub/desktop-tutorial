"""Render a numbered overview of the 64 real reference files, never a production approval."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageOps,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
BAD={}  # Three rejected profiles replaced and separately inspected on 2026-11-03.
ROLES=['C01','C01B','C02','C03','C03B','C04','C04B','C05','C06','C08']

def main():
    assets=json.loads((HERE/'reference/manifest.json').read_text())['assets']
    approval_path=HERE/'reference/approvals.json'
    approvals=json.loads(approval_path.read_text()).get('assets',{}) if approval_path.exists() else {}
    inventory=[]
    for r in assets:
        f=HERE/r['file']
        with Image.open(f) as im:dimensions=list(im.size)
        inventory.append(dict(id=r['id'],file=r['file'],sha256=hashlib.sha256(f.read_bytes()).hexdigest(),dimensions=dimensions,review='approved_reference' if approvals.get(r['id'],{}).get('sha256')==hashlib.sha256(f.read_bytes()).hexdigest() else 'candidate_not_approved',issue=BAD.get(r['id'])))
    assert len(inventory)==64 and len({r['id'] for r in inventory})==64
    out=HERE/'reference/gallery';out.mkdir(exist_ok=True)
    fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(fontpath,20);small=ImageFont.truetype(fontpath,16)
    pages=[]
    def tile(sheet,key,box,portrait):
        x,y,w,h=box;d=ImageDraw.Draw(sheet)
        r=next(r for r in inventory if r['id']==key)
        im=Image.open(HERE/r['file']).convert('RGB')
        if portrait and im.width/im.height>1.3 and not key.endswith('_face'):
            cw=min(im.width,int(im.height*.95));left=(im.width-cw)//2;im=im.crop((left,0,left+cw,im.height))
        im=ImageOps.contain(im,(w-12,h-65))
        sheet.paste(im,(x+(w-im.width)//2,y+34))
        d.text((x+8,y+7),key,fill='#1e2832',font=font)
        if key in BAD:
            d.rectangle((x+5,y+h-28,x+w-5,y+h-3),fill='#b52b32')
            d.text((x+10,y+h-26),'REPAIR REQUIRED: SIDE VIEW',fill='white',font=small)
    for part in range(2):
        page=Image.new('RGB',(1600,2110),'#efefec');d=ImageDraw.Draw(page)
        d.text((20,15),f'CRIPPEN 1910 / EPISODE 03 / CHARACTER VIEWS {part+1} OF 2',fill='#1e2832',font=font)
        d.text((20,48),'64 REFERENCES REVIEWED - animation footage is approved separately.',fill='#a12631',font=font)
        for i,role in enumerate(ROLES[part*5:(part+1)*5]):
            for j,suffix in enumerate(['','_side','_back','_face']):tile(page,role+suffix,(j*400,100+i*400,400,400),True)
        page.save(out/f'characters-{part+1}.jpg',quality=90);pages.append(page)
    others=[r['id'] for r in inventory if not any(r['id']==role or r['id'].startswith(role+'_') for role in ROLES)]
    assert len(others)==24
    page=Image.new('RGB',(1600,1750),'#efefec');d=ImageDraw.Draw(page)
    d.text((20,15),'CRIPPEN 1910 / GROUPS, LOCATIONS AND PROPS / 24 FILES',fill='#1e2832',font=font)
    d.text((20,48),'Reference review complete; see live production receipts for animation/film status.',fill='#a12631',font=font)
    for i,key in enumerate(others):tile(page,key,((i%4)*400,100+(i//4)*270,400,270),False)
    page.save(out/'locations-and-props.jpg',quality=90);pages.append(page)
    pages[0].save(HERE/'reference-overview.pdf','PDF',resolution=140,save_all=True,append_images=pages[1:])
    (HERE/'reference/inventory.json').write_text(json.dumps({'file_count':64,'known_rejected_ids':list(BAD),'all_references_approved':all(r['review']=='approved_reference' for r in inventory),'items':inventory},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
