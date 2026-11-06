# -*- coding: utf-8 -*-
import io, base64, os, html, json, shutil
from PIL import Image, ImageOps
WEBDIR="/mnt/user-data/outputs/web"
SITE="/mnt/user-data/outputs/site"
os.makedirs(SITE, exist_ok=True)
BASE="/mnt/user-data/uploads/영국"
DIRS=[BASE+"/Photos-1-00%d"%i for i in range(1,7)]
def resolve(fn):
    for d in DIRS:
        p=os.path.join(d,fn)
        if os.path.exists(p): return p
NOINDEX='<meta name="robots" content="noindex, nofollow">'

# day page: web file -> ascii name, inject noindex
pages=[
 ("런던여행기_1028-29.html","day1-2.html","Day 1·2","10.28–29 (수·목)","런던 도착 · 박물관과 뮤지컬","DSCF3090.JPG"),
 ("런던여행기_1030.html","day3.html","Day 3","10.30 (금)","해리포터 스튜디오와 런던 야경","20261030_105133.jpg"),
 ("런던여행기_1031.html","day4.html","Day 4","10.31 (토)","리치몬드 파크, 그리고 레스터로","20261031_121324.jpg"),
 ("런던여행기_1101.html","day5.html","Day 5","11.01 (일)","레스터 — 포니콘","20261101_165007.jpg"),
 ("런던여행기_1102.html","day6.html","Day 6","11.02 (월)","런던으로 · 세인트폴과 버로우마켓","20261102_130728.jpg"),
 ("런던여행기_1103.html","day7.html","Day 7","11.03 (화)","과학박물관, 그리고 귀국","20261103_092043.jpg"),
]
for src,dst,_,_,_,_ in pages:
    s=open(os.path.join(WEBDIR,src),encoding="utf-8").read()
    if NOINDEX not in s:
        s=s.replace('<meta charset="utf-8">','<meta charset="utf-8">'+NOINDEX,1)
    # add a back-to-home link in the footer
    s=s.replace('<footer>런던 가족 여행기 · 2026</footer>',
                '<footer><a href="index.html" style="color:#2c6e7f;text-decoration:none;font-weight:600">← 전체 목록</a></footer>')
    open(os.path.join(SITE,dst),"w",encoding="utf-8").write(s)
    print("wrote",dst,round(os.path.getsize(os.path.join(SITE,dst))/1048576,1),"MB")

def thumb(fn, side=680, q=78):
    im=ImageOps.exif_transpose(Image.open(resolve(fn))).convert("RGB")
    w,h=im.size; s=side/float(min(w,h)); im=im.resize((round(w*s),round(h*s)),Image.LANCZOS)
    tw,th=side,int(side*0.72); W,H=im.size; l=(W-tw)//2; t=(H-th)//2; im=im.crop((l,t,l+tw,t+th))
    b=io.BytesIO(); im.save(b,"JPEG",quality=q,optimize=True)
    return "data:image/jpeg;base64,"+base64.b64encode(b.getvalue()).decode()
def esc(s): return html.escape(s,quote=True)
cards=""
for src,dst,tag,date,sub,img in pages:
    uri=thumb(img)
    cards+=('<a class="card" href="'+dst+'">'
            '<div class="thumb"><img src="'+uri+'" alt="" loading="lazy"><span class="tag">'+esc(tag)+'</span></div>'
            '<div class="cbody"><div class="cdate">'+esc(date)+'</div><div class="csub">'+esc(sub)+'</div></div>'
            '<span class="go">여행기 보기 →</span></a>')
CSS=open("/home/claude/index_css.txt").read()
doc='<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'+NOINDEX
doc+='<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
doc+='<title>런던 가족 여행기 2026</title>'
doc+='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Noto+Sans+KR:wght@400;500;700&display=swap">'
doc+='<style>'+CSS+'</style></head><body>'
doc+='<div class="wrap"><header><div class="eyebrow">LONDON FAMILY TRIP</div>'
doc+='<h1>런던 가족 여행기</h1><div class="dates">2026. 10. 28 – 11. 03 · 7일간의 기록</div>'
doc+='<div class="intro">아빠와 딸의 런던·레스터 7일. 날짜를 눌러 그날의 사진과 동선을 따라가 보세요.</div></header>'
doc+='<div class="grid">'+cards+'</div>'
doc+='<footer>사진 속 지도는 그날의 이동 순서예요 · 각 사진을 누르면 크게 넘겨볼 수 있어요</footer>'
doc+='</div></body></html>'
open(os.path.join(SITE,"index.html"),"w",encoding="utf-8").write(doc)
print("wrote index.html",round(os.path.getsize(os.path.join(SITE,'index.html'))/1024,1),"KB")
