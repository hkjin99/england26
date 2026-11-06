# -*- coding: utf-8 -*-
import os, io, base64, json, math, html
from PIL import Image, ImageOps
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for _fp in ["/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf","/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]:
    try:
        import os as _os
        if _os.path.exists(_fp): fm.fontManager.addfont(_fp)
    except: pass
_KRPATHS=["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]
KRFONT=None
for _p in _KRPATHS:
    import os as _os
    if _os.path.exists(_p):
        try:
            fm.fontManager.addfont(_p); KRFONT=fm.FontProperties(fname=_p); break
        except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

BASE = "/mnt/user-data/uploads/영국"
SRCDIRS = [BASE+"/Photos-1-001", BASE+"/Photos-1-002", BASE+"/Photos-1-003",
           BASE+"/Photos-1-004", BASE+"/Photos-1-005", BASE+"/Photos-1-006"]
OUTDIR = os.environ.get("OUTDIR","/mnt/user-data/outputs")
os.makedirs(OUTDIR, exist_ok=True)
WEB = os.environ.get("WEB")=="1"   # web/hosting build: smaller images, read-only (no story boxes/save), no photo numbers

_RESOLVE={}
def _index():
    for d in SRCDIRS:
        if not os.path.isdir(d): continue
        for fn in os.listdir(d):
            _RESOLVE.setdefault(fn, os.path.join(d,fn))
_index()
def resolve(fn):
    return _RESOLVE.get(fn, os.path.join(SRCDIRS[0],fn))

LANDMARKS = [
 ("히드로 공항",51.4700,-0.4543),("패딩턴",51.5154,-0.1755),("리틀베니스",51.5222,-0.1830),
 ("자연사박물관",51.4967,-0.1764),("V&A",51.4966,-0.1719),("과학박물관",51.4978,-0.1745),
 ("하이드파크",51.5073,-0.1657),("켄싱턴 가든",51.5055,-0.1792),("버킹엄궁",51.5014,-0.1419),
 ("웨스트민스터",51.4995,-0.1248),("런던아이",51.5033,-0.1196),("코벤트가든",51.5123,-0.1240),
 ("라이세움 극장",51.5115,-0.1200),("트라팔가 광장",51.5080,-0.1281),("소호",51.5130,-0.1320),
 ("타워브리지",51.5055,-0.0754),("런던탑",51.5081,-0.0759),("세인트폴",51.5138,-0.0984),
 ("버로우마켓",51.5055,-0.0909),("킹스크로스",51.5308,-0.1238),("베이커스트리트",51.5226,-0.1571),
 ("해리포터 스튜디오",51.6908,-0.4186),
 ("리치몬드 파크",51.4495,-0.2761),("리치몬드 파크",51.4380,-0.2870),("리치몬드역",51.4630,-0.3010),
 ("레스터",52.6327,-1.1387),("레스터",52.6340,-1.1250),("레스터",52.6026,-1.0788),
 ("인천공항",37.4602,126.4407),
]

def hav(a,b,c,d):
    R=6371000; p1=math.radians(a); p2=math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

import datetime as _dt
def _fntime(bn):
    import re
    m=re.match(r'(20\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',bn)
    if m: return "%s:%s:%s %s:%s:%s"%m.groups()
    return None

def read_meta(p):
    bn=os.path.basename(p)
    im=Image.open(p); ex=im.getexif()
    # capture time only: DateTimeOriginal, else Digitized. Never the file-modified time (0x0132).
    dt=None
    try:
        sub=ex.get_ifd(0x8769); dt=sub.get(0x9003) or sub.get(0x9004)
    except: pass
    if not dt: dt=_fntime(bn)          # phone filename encodes local capture time
    make=""
    try: make=(ex.get(0x010F) or "")
    except: pass
    is_fuji = ("FUJI" in str(make).upper()) or bn.upper().startswith("DSCF")
    # timezone offset the photo was stamped in (OffsetTimeOriginal/Digitized), e.g. "+09:00" (KST) or "+00:00" (UK)
    off=None
    try:
        sub=ex.get_ifd(0x8769); off=sub.get(0x9011) or sub.get(0x9012)
    except: pass
    offh=None
    if off:
        try:
            s=1 if off[0]=="+" else -1; hh,mm=off[1:].split(":"); offh=s*(int(hh)+int(mm)/60.0)
        except: offh=None
    if offh is None: offh = 9.0 if is_fuji else 0.0   # fallback when the tag is missing
    lat=lon=None
    try:
        g=ex.get_ifd(0x8825)
        if g and 2 in g and 4 in g:
            def dms(v): return float(v[0])+float(v[1])/60+float(v[2])/3600
            lat=dms(g[2]); lat=-lat if g.get(1)=="S" else lat
            lon=dms(g[4]); lon=-lon if g.get(3)=="W" else lon
    except: pass
    # Normalize every photo to UK time (GMT=UTC+0 in late Oct) using its own stamped offset.
    secs=None; ep=None; jday=None; date=None; time=""; otime=""; odate=None
    d=None
    if dt:
        try: d=_dt.datetime.strptime(dt,"%Y:%m:%d %H:%M:%S")
        except: d=None
    if d is not None:
        otime=d.strftime("%H:%M"); odate=d.date().isoformat()   # original local (as-shot) time, e.g. KST for the Incheon photo
        if offh: d=d-_dt.timedelta(hours=offh)
        ep=(d-_dt.datetime(2026,1,1)).total_seconds()
        jday=(d-_dt.timedelta(hours=5)).date().isoformat()  # 5am boundary: late-night photos join the previous day
        date=d.date().isoformat()
        secs=d.hour*3600+d.minute*60+d.second
        time=d.strftime("%H:%M")
        dt=d.strftime("%Y:%m:%d %H:%M:%S")
    return {"dt":dt,"lat":lat,"lon":lon,"secs":secs,"ep":ep,"jday":jday,"date":date,"fuji":is_fuji,"time":time,"otime":otime,"odate":odate}

def nearest_landmark(lat,lon,maxm=850):
    if lat is None: return ""
    best=None;bd=1e9
    for nm,la,lo in LANDMARKS:
        d=hav(lat,lon,la,lo)
        if d<bd: bd=d;best=nm
    return best if bd<=maxm else ""

def data_uri(p, maxside=None, q=None):
    if maxside is None: maxside = 1024 if WEB else 1120
    if q is None: q = 74 if WEB else 77
    im=ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    w,h=im.size; s=min(1.0, maxside/float(max(w,h)))
    if s<1.0: im=im.resize((round(w*s),round(h*s)), Image.LANCZOS)
    b=io.BytesIO(); im.save(b,"JPEG",quality=q,optimize=True)
    return "data:image/jpeg;base64,"+base64.b64encode(b.getvalue()).decode()

MAXINH = 150*60  # don't inherit GPS from a photo more than 2.5h away in time (avoids pulling a flight-crossing location)

def build_photos(files, start=1):
    recs=[]
    for fn in files:
        m=read_meta(resolve(fn)); m["file"]=fn; recs.append(m)
    # order by absolute time (ep) so post-midnight photos stay in true sequence
    recs.sort(key=lambda r:(r["ep"] if r["ep"] is not None else 9e18, r["file"]))
    # inherit GPS from nearest-in-time photo that HAS gps, but only if close enough in time
    have=[r for r in recs if r["lat"] is not None and r["ep"] is not None]
    for r in recs:
        if r["lat"] is None and have and r["ep"] is not None:
            nb=min(have,key=lambda h:abs(h["ep"]-r["ep"]))
            if abs(nb["ep"]-r["ep"])<=MAXINH:
                r["lat"]=nb["lat"]; r["lon"]=nb["lon"]; r["inherited"]=True
    for i,r in enumerate(recs,start): r["idx"]=i   # sequence number (time order), continuous across the file
    return recs

def group_moments(recs, gap=20*60, dist=500):
    groups=[]; cur=[]
    for r in recs:
        if not cur: cur=[r]; continue
        prev=cur[-1]
        far=False
        if r["ep"] is not None and prev["ep"] is not None and abs(r["ep"]-prev["ep"])>gap: far=True
        if r["lat"] and prev["lat"] and hav(prev["lat"],prev["lon"],r["lat"],r["lon"])>dist: far=True
        if far: groups.append(cur); cur=[r]
        else: cur.append(r)
    if cur: groups.append(cur)
    return groups

# ---- manual overrides (by continuous photo number / idx) ----
KST_IDX = {1}   # photos to show in their as-shot local time (KST) instead of UK time
# force these idx ranges into single blocks with the given location label; None label = keep auto label
FORCE_GROUPS = [
    (23,27,"자연사박물관"),
    (28,48,"자연사박물관"),
    (49,57,"V&A"),
    (58,62,"놀이터"),
]

def group_with_forced(recs, forced):
    """Group recs, but force any idx range in `forced` into one block (with its label).
    Returns a list of (group_recs, forced_label_or_None)."""
    def keyof(idx):
        for k,(s,e,l) in enumerate(forced):
            if s<=idx<=e: return k
        return None
    out=[]; free=[]; cur=[]; curk=[None]
    def flush_free():
        if free:
            for g in group_moments(free): out.append((g,None))
            free[:]=[]
    def flush_cur():
        if cur:
            out.append((cur[:],forced[curk[0]][2])); cur[:]=[]; curk[0]=None
    for r in recs:
        k=keyof(r["idx"])
        if k is None:
            flush_cur(); free.append(r)
        else:
            flush_free()
            if cur and curk[0]==k: cur.append(r)
            else: flush_cur(); cur.append(r); curk[0]=k
    flush_cur(); flush_free()
    return out

def draw_map(groups, out_png):
    import statistics
    import matplotlib.patheffects as pe
    pts=[]
    for i,g in enumerate(groups,1):
        la=[p["lat"] for p in g if p["lat"]]; lo=[p["lon"] for p in g if p["lon"]]
        if not la: continue
        clat=sum(la)/len(la); clon=sum(lo)/len(lo)
        pts.append({"n":i,"lat":clat,"lon":clon,"label":nearest_landmark(clat,clon)})
    if not pts: return None
    lats=[p["lat"] for p in pts]; lons=[p["lon"] for p in pts]
    # --- bounds: zoom to the main metro cluster; clamp far-away outliers (another city) to the edge ---
    # center = the densest point (most neighbours within 20km); robust to multi-modal spreads
    def _nbr(pi): return sum(1 for pj in pts if hav(pi["lat"],pi["lon"],pj["lat"],pj["lon"])<=20000)
    center=max(pts,key=_nbr)
    core=[p for p in pts if hav(center["lat"],center["lon"],p["lat"],p["lon"])<=25000]  # same metro (~25km)
    outliers=[p for p in pts if p not in core]
    if outliers and len(core)>=2:
        bpts=core          # readable metro view; far outliers clamped to the edge
    else:
        bpts=pts           # all within one metro → show the whole extent
    blats=[p["lat"] for p in bpts]; blons=[p["lon"] for p in bpts]
    minlat,maxlat=min(blats),max(blats); minlon,maxlon=min(blons),max(blons)
    dlat=(maxlat-minlat) or 0.006; dlon=(maxlon-minlon) or 0.006
    # enforce a minimum frame span (~1.2km) so a tight cluster isn't over-zoomed
    MINSPAN=0.012
    if dlon<MINSPAN: c=(minlon+maxlon)/2; minlon=c-MINSPAN/2; maxlon=c+MINSPAN/2; dlon=MINSPAN
    if dlat<MINSPAN: c=(minlat+maxlat)/2; minlat=c-MINSPAN/2; maxlat=c+MINSPAN/2; dlat=MINSPAN
    pad=0.26
    minlat-=dlat*pad; maxlat+=dlat*pad; minlon-=dlon*pad; maxlon+=dlon*pad
    meanlat=(minlat+maxlat)/2; asp=1/math.cos(math.radians(meanlat))
    wspan=(maxlon-minlon); hspan=(maxlat-minlat)*asp
    fw=7.4; fh=max(3.4,min(8.0, fw*hspan/wspan if wspan else 4))
    # clamp a point into the frame; returns (x,y,outside?)
    def clamp(p):
        x=min(max(p["lon"],minlon+dlon*0.04),maxlon-dlon*0.04)
        y=min(max(p["lat"],minlat+dlat*0.04),maxlat-dlat*0.04)
        return x,y,(x!=p["lon"] or y!=p["lat"])
    fig,ax=plt.subplots(figsize=(fw,fh),dpi=150)
    fig.patch.set_facecolor("#f4efe6"); ax.set_facecolor("#eceee7")
    ax.grid(True,color="#dcd3c3",lw=.6,zorder=0)
    rx=[];ry=[]
    for p in pts:
        x,y,_=clamp(p); rx.append(x); ry.append(y)
    ax.plot(rx,ry,color="#2c6e7f",lw=2.2,ls=(0,(5,4)),zorder=3)
    shown=set(); halo=[pe.withStroke(linewidth=3,foreground="#f4efe6")]
    for p in pts:
        x,y,outside=clamp(p)
        ax.scatter([x],[y],s=235,color=("#9a6b1f" if outside else "#b8892b"),edgecolor="#1f3a5f",lw=1.5,zorder=4)
        ax.text(x,y,str(p["n"]),color="white",ha="center",va="center",fontsize=8.5,fontweight="bold",zorder=5)
        lab=p["label"]
        if outside and not lab: lab="(시외)"
        if lab and lab not in shown:
            shown.add(lab)
            dx,dy=(-12,10) if outside else (10,8)
            ha='right' if outside else 'left'
            ax.annotate(lab,(x,y),textcoords="offset points",xytext=(dx,dy),
                        fontsize=9,color="#23201b",zorder=6,ha=ha,
                        fontproperties=KRFONT,path_effects=halo)
    ax.set_xlim(minlon,maxlon); ax.set_ylim(minlat,maxlat); ax.set_aspect(asp)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_edgecolor("#cdbfa6")
    fig.savefig(out_png,facecolor=fig.get_facecolor(),bbox_inches="tight",pad_inches=0.12)
    plt.close()
    return out_png

def png_data_uri(path):
    return "data:image/png;base64,"+base64.b64encode(open(path,"rb").read()).decode()

# ---------- HTML ----------
CSS = r'''
:root{--paper:#f4efe6;--card:#fffdf8;--ink:#23201b;--muted:#7a7266;--line:#e2d9c9;
--navy:#1f3a5f;--teal:#2c6e7f;--gold:#b8892b;
--serif:"Gowun Batang",serif;--sans:"Noto Sans KR",system-ui,sans-serif;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.65}
.page{max-width:780px;margin:0 auto;padding:0 20px 90px}
.cover{text-align:center;padding:52px 0 26px;border-bottom:1px solid var(--line);margin-bottom:6px}
.eyebrow{font-size:.7rem;letter-spacing:.3em;color:var(--teal);font-weight:700}
.cover h1{font-family:var(--serif);font-weight:700;font-size:3rem;margin:.18em 0 .1em;color:var(--navy);letter-spacing:-.01em;line-height:1.1}
.subt{font-family:var(--serif);font-size:1.15rem;color:var(--muted)}
section{margin:32px 0}
h2{font-family:var(--serif);font-size:1.12rem;color:var(--navy);margin:0 0 12px;display:flex;align-items:center;gap:10px}
h2:after{content:"";flex:1;height:1px;background:var(--line)}
.ef{outline:none;transition:.15s;border-radius:7px}
.ef:empty{display:none}
.ef:empty:before{content:"";color:#b4a992}
.dayintro{font-family:var(--serif);font-size:1.05rem;color:var(--ink)}
body.editing .ef{display:inline-block;min-height:1.2em}
body.editing .dayintro{display:block;min-height:3em;background:var(--card);box-shadow:inset 0 0 0 1px var(--line);padding:12px 14px;font-size:1.02rem}
body.editing .ef:not(.dayintro){background:rgba(44,110,127,.07);box-shadow:inset 0 0 0 1px var(--teal);padding:2px 7px}
body.editing .ef:empty:before{content:attr(data-ph)}
.loc{display:inline-flex;gap:3px;align-items:baseline}
body:not(.editing) .loc:has(.locname:empty){display:none}
.mapimg{width:100%;border-radius:14px;border:1px solid var(--line);display:block;box-shadow:0 2px 4px rgba(0,0,0,.05)}
.maphint{font-size:.8rem;color:var(--muted);margin-top:8px}
.moments{display:flex;flex-direction:column;gap:30px}
.moment{margin:0}
.mhead{display:flex;gap:11px;align-items:baseline;margin:0 2px 9px;font-size:.84rem;color:var(--muted)}
.mhead .time{font-weight:700;color:var(--gold);font-variant-numeric:tabular-nums}
.mhead .tz{font-weight:600;color:var(--muted);font-size:.9em}
.photos{display:grid;gap:8px;grid-template-columns:repeat(3,1fr)}
.photos[data-n="1"]{grid-template-columns:1fr}
.photos[data-n="2"],.photos[data-n="4"]{grid-template-columns:repeat(2,1fr)}
.photo{position:relative;margin:0}
.photo img{display:block;width:100%;cursor:zoom-in;border-radius:11px;background:#000;box-shadow:0 2px 4px rgba(0,0,0,.06),0 8px 20px rgba(0,0,0,.09)}
.photos:not([data-n="1"]) .photo img{aspect-ratio:4/3;object-fit:cover}
.photo img:hover{opacity:.95}
.pnum{position:absolute;top:8px;left:8px;z-index:6;background:rgba(31,58,95,.82);color:#fff;font-size:.72rem;font-weight:700;line-height:1;padding:4px 7px;border-radius:7px;font-variant-numeric:tabular-nums;pointer-events:none;box-shadow:0 1px 3px rgba(0,0,0,.45)}
.cap{margin-top:7px;font-size:.92rem;color:var(--ink);line-height:1.5;white-space:pre-wrap}
.cap:empty{display:none}
body.editing .cap{display:block;min-height:1.3em}
body.editing .photo{cursor:grab}
body.editing .photo img{cursor:grab}
.photo.dragging{opacity:.35}
.photo.dropbefore::before{content:"";position:absolute;left:-5px;top:0;bottom:0;width:3px;background:var(--teal);border-radius:2px}
.photo.dropafter::after{content:"";position:absolute;right:-5px;top:0;bottom:0;width:3px;background:var(--teal);border-radius:2px}
body.editing .photos{outline:2px dashed transparent;outline-offset:5px;border-radius:12px}
body.editing .photos.dropzone{outline-color:var(--teal)}
footer{text-align:center;color:var(--muted);font-size:.8rem;margin-top:50px;padding-top:20px;border-top:1px solid var(--line)}
#lightbox{position:fixed;inset:0;background:rgba(15,12,8,.93);display:none;align-items:center;justify-content:center;z-index:2000;cursor:zoom-out;padding:18px}
#lightbox img{max-width:92%;max-height:94%;border-radius:8px;box-shadow:0 10px 50px rgba(0,0,0,.6);cursor:pointer}
.lbnav{position:fixed;top:50%;transform:translateY(-50%);z-index:2001;background:rgba(255,255,255,.14);color:#fff;border:none;width:52px;height:52px;border-radius:50%;font-size:1.9rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:.15s;-webkit-user-select:none;user-select:none}
.lbnav:hover{background:rgba(255,255,255,.28)}
.lbprev{left:12px}.lbnext{right:12px}
.lbcount{position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:2001;color:#fff;background:rgba(0,0,0,.4);padding:5px 13px;border-radius:999px;font-size:.85rem;font-weight:600;font-variant-numeric:tabular-nums}
.lbclose{position:fixed;top:12px;right:14px;z-index:2001;background:rgba(255,255,255,.14);color:#fff;border:none;width:42px;height:42px;border-radius:50%;font-size:1.3rem;cursor:pointer}
.lbclose:hover{background:rgba(255,255,255,.28)}
@media(max-width:520px){.lbnav{width:44px;height:44px;font-size:1.6rem}}
.topbar{position:fixed;top:9px;right:12px;z-index:1700;display:flex;gap:13px;font-size:.74rem;font-weight:700;letter-spacing:.09em}
.topbar a{color:var(--muted);text-decoration:none;cursor:pointer;opacity:.5;transition:.15s;padding:3px 2px}
.topbar a:hover{opacity:1;color:var(--navy)}
.topbar a.on{opacity:1;color:var(--teal)}
#editBanner{position:fixed;left:0;right:0;top:0;z-index:1650;background:var(--teal);color:#fff;text-align:center;font-size:.78rem;font-weight:600;padding:5px;display:none}
body.editing #editBanner{display:block}
body.editing{padding-top:28px}
.toast{position:fixed;left:50%;bottom:78px;transform:translateX(-50%) translateY(10px);background:var(--navy);color:#fff;padding:10px 18px;border-radius:999px;font-size:.85rem;font-weight:600;opacity:0;transition:.25s;z-index:1600;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%)}
.day+.day{margin-top:30px;border-top:3px double var(--line)}
body.web .pnum{display:none}
body.web.editing .pnum{display:block}
.homelink{color:var(--teal);text-decoration:none;font-weight:600}
.homelink:hover{text-decoration:underline}
@media(max-width:520px){.cover h1{font-size:2.3rem}.grid.c3{grid-template-columns:repeat(2,1fr)}}
'''

JS = r'''
function editing(){return document.body.classList.contains('editing');}
/* ---- lightbox ---- */
var LBimgs=[],LBi=0;
function openLB(el){if(editing())return;LBimgs=[].slice.call(document.querySelectorAll('.photo img'));LBi=LBimgs.indexOf(el);if(LBi<0)LBi=0;showLB();document.getElementById('lightbox').style.display='flex';}
function showLB(){var lb=document.getElementById('lightbox');lb.querySelector('img').src=LBimgs[LBi].src;var c=document.getElementById('lbcount');if(c)c.textContent=(LBi+1)+' / '+LBimgs.length;}
function lbNext(e){if(e){e.stopPropagation();}if(!LBimgs.length)return;LBi=(LBi+1)%LBimgs.length;showLB();}
function lbPrev(e){if(e){e.stopPropagation();}if(!LBimgs.length)return;LBi=(LBi-1+LBimgs.length)%LBimgs.length;showLB();}
function closeLB(){document.getElementById('lightbox').style.display='none';}
document.addEventListener('keydown',function(e){var lb=document.getElementById('lightbox');if(!lb||lb.style.display!=='flex')return;if(e.key==='ArrowRight')lbNext();else if(e.key==='ArrowLeft')lbPrev();else if(e.key==='Escape')closeLB();});
function toast(m){var t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(function(){t.classList.remove('show');},2200);}
/* ---- text autosave (this browser only) ---- */
var KEY=(document.body.dataset.key||'journal')+'_txt';
function store(){var o={};document.querySelectorAll('.ef').forEach(function(e){o[e.dataset.k]=e.innerHTML;});try{localStorage.setItem(KEY,JSON.stringify(o));}catch(e){}}
(function(){try{var o=JSON.parse(localStorage.getItem(KEY)||'{}');document.querySelectorAll('.ef').forEach(function(e){var v=o[e.dataset.k];if(v&&v.trim()&&!e.innerHTML.trim())e.innerHTML=v;});}catch(e){}})();
document.addEventListener('input',function(e){if(e.target.classList&&e.target.classList.contains('ef'))store();});
/* ---- password (light protection; client-side) ---- */
function pwhash(s){var h=5381;for(var i=0;i<s.length;i++){h=((h<<5)+h+s.charCodeAt(i))>>>0;}return h.toString(36);}
function checkPw(act){var cur=document.body.dataset.pwhash||'';
 if(!cur){var p1=prompt(act+' — 이 여행기를 보호할 비밀번호를 정하세요 (최초 1회):');if(p1===null)return false;if(!p1){alert('비밀번호가 비어 있어요.');return false;}document.body.dataset.pwhash=pwhash(p1);return true;}
 var p=prompt(act+' — 비밀번호를 입력하세요:');if(p===null)return false;if(pwhash(p)!==cur){alert('비밀번호가 올바르지 않아요.');return false;}return true;}
/* ---- edit mode ---- */
function setEditing(on){document.body.classList.toggle('editing',on);
 document.querySelectorAll('.ef').forEach(function(e){e.contentEditable=on?'true':'false';});
 document.querySelectorAll('.photo').forEach(function(p){if(on)p.setAttribute('draggable','true');else p.removeAttribute('draggable');});
 var le=document.getElementById('lnkEdit');if(le){le.textContent=on?'VIEW':'EDIT';le.classList.toggle('on',on);}}
function toggleEdit(){if(editing()){setEditing(false);toast('보기 모드로 돌아왔어요');return;}if(checkPw('편집'))setEditing(true);}
function updateCounts(){document.querySelectorAll('.photos').forEach(function(ps){ps.dataset.n=ps.querySelectorAll('.photo').length;});}
/* ---- save (bake current state to a view-locked file) ---- */
function saveFile(){if(!checkPw('저장'))return;store();updateCounts();setEditing(false);
 document.querySelectorAll('.dragging,.dropbefore,.dropafter,.dropzone').forEach(function(e){e.classList.remove('dragging','dropbefore','dropafter','dropzone');});
 var html='<!DOCTYPE html>\n'+document.documentElement.outerHTML;var blob=new Blob([html],{type:'text/html'});
 var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(document.title||'여행기')+'.html';document.body.appendChild(a);a.click();a.remove();
 toast('저장됐어요 — 이 파일을 올리거나 공유하세요');}
/* ---- drag & drop photos between groups ---- */
var dragEl=null;
document.addEventListener('dragstart',function(e){if(!editing())return;var ph=e.target.closest&&e.target.closest('.photo');if(!ph)return;dragEl=ph;ph.classList.add('dragging');e.dataTransfer.effectAllowed='move';try{e.dataTransfer.setData('text/plain','x');}catch(_){}});
document.addEventListener('dragend',function(){if(dragEl)dragEl.classList.remove('dragging');document.querySelectorAll('.dropbefore,.dropafter,.dropzone').forEach(function(x){x.classList.remove('dropbefore','dropafter','dropzone');});dragEl=null;updateCounts();});
document.addEventListener('dragover',function(e){if(!dragEl)return;e.preventDefault();e.dataTransfer.dropEffect='move';
 var ph=e.target.closest&&e.target.closest('.photo');var zone=e.target.closest&&e.target.closest('.photos');
 document.querySelectorAll('.dropbefore,.dropafter').forEach(function(x){x.classList.remove('dropbefore','dropafter');});
 document.querySelectorAll('.photos').forEach(function(z){z.classList.toggle('dropzone',z===zone);});
 if(ph&&ph!==dragEl){var r=ph.getBoundingClientRect();ph.classList.add((e.clientX-r.left)>r.width/2?'dropafter':'dropbefore');}});
document.addEventListener('drop',function(e){if(!dragEl)return;e.preventDefault();
 var ph=e.target.closest&&e.target.closest('.photo');var zone=e.target.closest&&e.target.closest('.photos');
 if(ph&&ph!==dragEl){var r=ph.getBoundingClientRect();if((e.clientX-r.left)>r.width/2)ph.after(dragEl);else ph.before(dragEl);}
 else if(zone){zone.appendChild(dragEl);}
 document.querySelectorAll('.dropbefore,.dropafter,.dropzone').forEach(function(x){x.classList.remove('dropbefore','dropafter','dropzone');});
 updateCounts();});
'''

def esc(s): return html.escape(s, quote=True)

# Labels for photos that have no GPS but whose place we know (shown as text only; NOT plotted on the map)
MANUAL_LABEL = {
    "DSCF2984.JPG": "인천공항",
    "20261028_123639.jpg": "기내 (비행 중)",
}

def _mdlabel(dstr):
    try:
        y,m,d=dstr.split("-"); return str(int(m))+"/"+str(int(d))+" "
    except: return ""

def render_moment(g, gi, daykey, primary_date=None, forced_label=None, kst_idx=None):
    p0=g[0]
    kst = p0["idx"] in (kst_idx or set())
    if kst:
        tfirst=p0.get("otime") or p0["time"]; tlast=g[-1].get("otime") or g[-1]["time"]
    else:
        tfirst=p0["time"]; tlast=g[-1]["time"]
    trange=tfirst if (tfirst==tlast or not tlast) else (tfirst+"–"+tlast)
    # show the date when a photo's date differs from the day's main date (e.g. Incheon = night before in UK time)
    cmp_date = (p0.get("odate") if kst else p0.get("date"))
    if primary_date and cmp_date and cmp_date!=primary_date:
        trange=_mdlabel(cmp_date)+trange
    tzhtml=' <span class="tz">(한국시간)</span>' if kst else ''
    loc=forced_label or MANUAL_LABEL.get(p0["file"]) or (nearest_landmark(p0["lat"],p0["lon"]) if p0["lat"] else "")
    mid=daykey+'_m'+str(gi)
    head=('<div class="mhead"><span class="time">'+esc(trange)+tzhtml+'</span>'
          '<span class="loc">📍 <span class="locname ef" data-k="'+mid+'_name" data-ph="장소 이름">'+esc(loc)+'</span></span></div>')
    n=len(g)
    photos=''
    for p in g:
        photos+=('<figure class="photo" data-k="'+daykey+'_p'+str(p["idx"])+'">'
                 '<span class="pnum">'+str(p["idx"])+'</span>'
                 '<img src="'+p["uri"]+'" loading="lazy" alt="" draggable="false" onclick="openLB(this)">'
                 '<figcaption class="cap ef" data-k="'+daykey+'_c'+str(p["idx"])+'" data-ph="사진 설명…"></figcaption>'
                 '</figure>')
    body='<div class="photos" data-n="'+str(n)+'">'+photos+'</div>'
    return '<div class="moment" id="'+mid+'">'+head+body+'</div>'

def render_day_block(day_no, date_label, subtitle, files, daykey, start_idx, forced=None, kst_idx=None):
    """Render one day as a stacked block (header + story + map + photos). Returns (html, next_idx, ngroups)."""
    recs=build_photos(files, start=start_idx)
    for r in recs: r["uri"]=data_uri(resolve(r["file"]))
    glist=group_with_forced(recs, forced or [])   # [(group_recs, forced_label_or_None), ...]
    groups=[g for g,_ in glist]
    mp=draw_map(groups, OUTDIR+"/map_"+daykey+".png")
    mapuri=png_data_uri(mp) if mp else None
    # primary date = most common UK date among the day's photos
    from collections import Counter
    dc=Counter(r["date"] for r in recs if r.get("date"))
    primary_date=dc.most_common(1)[0][0] if dc else None
    moments='\n'.join(render_moment(g,i+1,daykey,primary_date,flab,kst_idx) for i,(g,flab) in enumerate(glist))
    mapsec=''
    if mapuri:
        mapsec=('<section><h2>이 날의 이동</h2><img class="mapimg" src="'+mapuri+'" alt="이동 경로 지도">'
                '<div class="maphint">GPS가 있는 사진을 촬영 시각 순으로 이은 동선이에요 (지도 위 숫자는 이동 순서).</div></section>')
    h='<section class="day" id="'+daykey+'">'
    h+='<header class="cover"><div class="eyebrow">LONDON FAMILY TRIP · 2026</div>'
    h+='<h1>'+esc(date_label)+'</h1><div class="subt">'+esc(subtitle)+'</div></header>'
    h+='<section><h2>이 날의 이야기</h2><div class="dayintro ef" data-k="'+daykey+'_intro" data-ph="이 날 전체의 느낌을 자유롭게 적어보세요."></div></section>'
    h+=mapsec
    h+='<section><h2>사진과 기록</h2><div class="moments">'+moments+'</div></section>'
    h+='</section>'
    nxt=start_idx+len(recs)
    return h, nxt, len(groups)

def render_page(title, blocks_html, pagekey):
    doc='<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
    doc+='<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    doc+='<title>'+esc(title)+'</title>'
    doc+='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Noto+Sans+KR:wght@400;500;700&display=swap">'
    doc+='<style>'+CSS+'</style></head>'
    doc+='<body class="'+('web' if WEB else '')+'" data-key="journal_'+pagekey+'" data-pwhash="">'
    doc+='<div id="editBanner">편집 모드 — 글·장소 이름 수정, 사진을 끌어 옮길 수 있어요. 끝나면 SAVE</div>'
    doc+='<div class="topbar"><a id="lnkEdit" onclick="toggleEdit()">EDIT</a><a id="lnkSave" onclick="saveFile()">SAVE</a></div>'
    doc+='<div class="page">'+blocks_html
    foot='런던 가족 여행기 · 2026'
    doc+='<footer>'+foot+'</footer></div>'
    doc+=('<div id="lightbox" onclick="closeLB()">'
          '<div id="lbcount" class="lbcount"></div>'
          '<button class="lbclose" onclick="event.stopPropagation();closeLB()" aria-label="닫기">✕</button>'
          '<button class="lbnav lbprev" onclick="lbPrev(event)" aria-label="이전">‹</button>'
          '<img src="" alt="" onclick="lbNext(event)">'
          '<button class="lbnav lbnext" onclick="lbNext(event)" aria-label="다음">›</button>'
          '</div>')
    doc+='<div class="toast" id="toast"></div>'
    doc+='<script>'+JS+'</script></body></html>'
    return doc

def all_files():
    seen=set(); out=[]
    for d in SRCDIRS:
        if not os.path.isdir(d): continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith((".jpg",".jpeg",".png",".heic")) and fn not in seen:
                seen.add(fn); out.append(fn)
    return out

def bucket_by_jday(files):
    from collections import defaultdict
    b=defaultdict(list)
    for fn in files:
        m=read_meta(resolve(fn))
        b[m["jday"] or "NODATE"].append(fn)
    return b

def build_file(outfn, title, pagekey, blockdefs):
    """blockdefs: list of dicts {day_no,label,subtitle,files,daykey,forced,kst_idx}"""
    blocks=""; idx=1; info=[]
    for bd in blockdefs:
        h,idx,ng=render_day_block(bd["day_no"],bd["label"],bd["subtitle"],bd["files"],bd["daykey"],idx,
                                  bd.get("forced"),bd.get("kst_idx"))
        blocks+=h; info.append((len(bd["files"]),ng))
    doc=render_page(title, blocks, pagekey)
    outp=OUTDIR+"/"+outfn
    open(outp,"w",encoding="utf-8").write(doc)
    print("wrote",outfn,"|",info,"| idx",idx-1,"|",round(os.path.getsize(outp)/1048576,2),"MB")

if __name__=="__main__":
    files=all_files()
    buckets=bucket_by_jday(files)
    # ---- File 1: merged Day 1 (trip start incl. Incheon jday 10/27, + 10/28) + Day 2 (10/29), with the user's set-up overrides ----
    day1=buckets.get("2026-10-27",[])+buckets.get("2026-10-28",[])
    day2=buckets.get("2026-10-29",[])
    build_file("런던여행기_1028-29.html","런던 여행기 · 10월 28–29일","1028_29",[
        {"day_no":1,"label":"Day 1 — 10월 28일 (수)","subtitle":"런던 도착 (인천 출발)","files":day1,"daykey":"d1",
         "forced":FORCE_GROUPS,"kst_idx":KST_IDX},
        {"day_no":2,"label":"Day 2 — 10월 29일 (목)","subtitle":"박물관과 뮤지컬","files":day2,"daykey":"d2",
         "forced":FORCE_GROUPS,"kst_idx":KST_IDX},
    ])
    # ---- Single-day files (numbered from 1), no overrides yet ----
    singledays=[
        ("2026-10-30","런던여행기_1030.html","런던 여행기 · 10월 30일","1030",3,"Day 3 — 10월 30일 (금)","해리포터 스튜디오와 런던 야경","d3"),
        ("2026-10-31","런던여행기_1031.html","런던 여행기 · 10월 31일","1031",4,"Day 4 — 10월 31일 (토)","리치몬드 파크, 그리고 레스터로","d4"),
        ("2026-11-01","런던여행기_1101.html","런던 여행기 · 11월 1일","1101",5,"Day 5 — 11월 1일 (일)","레스터 — 포니콘","d5"),
        ("2026-11-02","런던여행기_1102.html","런던 여행기 · 11월 2일","1102",6,"Day 6 — 11월 2일 (월)","런던으로, 세인트폴과 버로우마켓","d6"),
        ("2026-11-03","런던여행기_1103.html","런던 여행기 · 11월 3일","1103",7,"Day 7 — 11월 3일 (화)","과학박물관, 그리고 귀국","d7"),
    ]
    for jd,outfn,title,pkey,dno,label,subtitle,dkey in singledays:
        fs=buckets.get(jd,[])
        if not fs: print("SKIP",jd); continue
        build_file(outfn,title,pkey,[{"day_no":dno,"label":label,"subtitle":subtitle,"files":fs,"daykey":dkey}])
