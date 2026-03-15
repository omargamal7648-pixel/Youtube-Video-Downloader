#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║       YouTube Downloader Pro                         ║
║       تصميم وتطوير: عمر جمال                        ║
╚══════════════════════════════════════════════════════╝

المتطلبات (تثبيت مرة واحدة):
    pip install flask yt-dlp

تشغيل البرنامج:
    python youtube_downloader.py

ثم افتح متصفحك على:  http://localhost:5000
"""

from flask import Flask, request, jsonify
import yt_dlp, threading, os, uuid, ssl

app = Flask(__name__)
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
downloads = {}

# السبب الحقيقي للخطأ: يوتيوب + HTTP/2 + بعض الـ ISPs المصرية
# الـ ISP بيتدخل في الـ TLS records على HTTP/2 → MAC corruption
# الحل النهائي: "http2": False = إجبار HTTP/1.1

YDL_BASE = {
    "quiet": True,
    "no_warnings": True,
    "nocheckcertificate": True,
    "legacy_server_connect": True, 
    "prefer_insecure": True,
    
    "retries": 15,
    "fragment_retries": 15,
    "extractor_retries": 5,
    "file_access_retries": 5,
    "sleep_interval_requests": 0.5,
    
    "concurrent_fragment_downloads": 4,
    
    "buffersize": 1024 * 32,
    "http_chunk_size": 2 * 1024 * 1024,
    
    "socket_timeout": 60,

    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"]
        }
    }
}

# ── HTML Interface ──────────────────────────────────────────────────────────
TEMPLATE = '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>YouTube Downloader Pro</title>\n<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">\n<style>\n:root{--bg:#07070E;--panel:#0F0F1C;--card:#161625;--card2:#1E1E33;--accent:#FF3D3D;--a2:#FF6B35;--gold:#FFB800;--green:#00E676;--blue:#448AFF;--muted:#5A5A7A;--bdr:#252540;--text:#EEEEFF;--fnt:\'Cairo\',sans-serif}\n*{margin:0;padding:0;box-sizing:border-box}html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--fnt);direction:rtl}\n::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:var(--panel)}::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:3px}\n.app{display:flex;height:100vh;overflow:hidden}\n.sb{width:235px;min-width:235px;background:var(--panel);border-left:1px solid var(--bdr);display:flex;flex-direction:column;padding-bottom:16px;position:relative;overflow:hidden}\n.sb::before{content:\'\';position:absolute;top:-80px;right:-80px;width:220px;height:220px;background:radial-gradient(circle,rgba(255,61,61,.12),transparent 70%);pointer-events:none}\n.brand{padding:20px 18px 16px;border-bottom:1px solid var(--bdr);margin-bottom:10px}\n.brand-icon{font-size:26px;display:block;margin-bottom:4px}\n.brand-name{font-size:16px;font-weight:900;background:linear-gradient(135deg,var(--accent),var(--a2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}\n.brand-sub{font-size:10px;color:var(--muted);margin-top:2px}\n.nl{font-size:10px;color:var(--muted);padding:4px 16px 6px;letter-spacing:1px}\n.nb{display:flex;align-items:center;gap:10px;padding:11px 14px;margin:2px 8px;border-radius:10px;cursor:pointer;transition:all .2s;font-size:13px;font-family:var(--fnt);font-weight:600;background:transparent;border:none;color:var(--muted);text-align:right;width:calc(100% - 16px)}\n.nb .ic{font-size:17px;min-width:26px}.nb:hover{background:var(--card2);color:var(--text)}\n.nb.active{background:linear-gradient(135deg,rgba(255,61,61,.18),rgba(255,107,53,.08));color:var(--text)}\n.sb-bot{margin-top:auto;padding:12px 14px 0}\n.dir-box{background:var(--card);border:1px solid var(--bdr);border-radius:10px;padding:10px 12px;margin-bottom:8px}\n.dir-lbl{font-size:10px;color:var(--muted);margin-bottom:4px}\n.dir-path{font-size:11px;color:var(--gold);word-break:break-all;direction:ltr;text-align:left}\n.btn-dir{width:100%;padding:8px;border-radius:8px;font-size:12px;font-family:var(--fnt);font-weight:600;background:var(--card2);border:1px solid var(--bdr);color:var(--text);cursor:pointer;transition:all .2s}\n.btn-dir:hover{border-color:var(--gold);color:var(--gold)}\n.sig{text-align:center;font-size:10px;color:var(--muted);padding-top:10px;border-top:1px solid var(--bdr)}\n.content{flex:1;overflow-y:auto;padding:26px 28px}\n.page{display:none;animation:fi .3s ease}.page.active{display:block}\n@keyframes fi{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}\n.ph{margin-bottom:22px}.pt{font-size:24px;font-weight:900}.ps{font-size:13px;color:var(--muted);margin-top:4px}\n.card{background:var(--card);border:1px solid var(--bdr);border-radius:14px;padding:18px;margin-bottom:14px}\n.ct{font-size:12px;font-weight:700;color:var(--muted);margin-bottom:10px}\n.ir{display:flex;gap:8px;align-items:stretch}\n.inp{flex:1;padding:11px 14px;background:var(--panel);border:1px solid var(--bdr);border-radius:9px;font-family:var(--fnt);font-size:13px;color:var(--text);transition:border-color .2s;direction:ltr;text-align:left}\n.inp:focus{outline:none;border-color:var(--accent)}.inp::placeholder{color:var(--muted)}\n.btn{padding:11px 18px;border-radius:9px;border:none;font-family:var(--fnt);font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;white-space:nowrap;display:inline-flex;align-items:center;gap:5px}\n.br{background:var(--accent);color:#fff}.br:hover{background:#CC3030;transform:translateY(-1px)}\n.bo{background:var(--a2);color:#fff}.bo:hover{background:#CC5520;transform:translateY(-1px)}\n.bg{background:var(--gold);color:#000}.bg:hover{background:#CC9400;transform:translateY(-1px)}\n.bgh{background:var(--card2);border:1px solid var(--bdr);color:var(--text)}.bgh:hover{border-color:var(--muted)}\n.bsm{padding:7px 12px;font-size:12px;border-radius:8px}\n.bfull{width:100%;justify-content:center;margin-top:10px;padding:13px;font-size:14px}\n.or{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px}\n.ol{font-size:12px;color:var(--muted);font-weight:600}\nselect{padding:8px 12px;background:var(--panel);border:1px solid var(--bdr);border-radius:8px;font-family:var(--fnt);font-size:12px;color:var(--text);cursor:pointer}\nselect:focus{outline:none;border-color:var(--accent)}\n.ib{background:var(--panel);border:1px solid var(--bdr);border-radius:9px;padding:12px 14px;font-size:13px;line-height:1.7;margin-top:10px;min-height:50px;display:flex;align-items:center;color:var(--muted)}\n.ib.loaded{color:var(--text);border-color:var(--green)}\n.pw{margin-top:10px}.po{height:7px;background:var(--panel);border-radius:4px;overflow:hidden}\n.pi{height:100%;width:0%;border-radius:4px;background:linear-gradient(90deg,var(--accent),var(--a2));transition:width .4s;position:relative;overflow:hidden}\n.pi::after{content:\'\';position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent);animation:sh 1.5s infinite}\n@keyframes sh{to{left:100%}}\n.ptxt{font-size:11px;color:var(--muted);margin-top:5px;text-align:center}\n.segs{display:flex;background:var(--panel);border-radius:9px;padding:3px;gap:2px}\n.seg{flex:1;padding:8px;border-radius:7px;border:none;text-align:center;font-family:var(--fnt);font-size:12px;font-weight:700;cursor:pointer;transition:all .2s;color:var(--muted);background:transparent}\n.seg.active{background:var(--accent);color:#fff}\n.plc{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap}\n.pll{max-height:380px;overflow-y:auto;border-radius:9px}\n.pli{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:1px solid var(--bdr);transition:background .15s}\n.pli:last-child{border-bottom:none}.pli:hover{background:rgba(255,255,255,.03)}\n.pli input[type=checkbox]{width:16px;height:16px;accent-color:var(--a2);cursor:pointer;flex-shrink:0}\n.pn{font-size:11px;color:var(--muted);min-width:26px;text-align:left}\n.ptit{flex:1;font-size:12px;font-weight:600;direction:rtl;text-align:right}\n.pdur{font-size:11px;color:var(--muted);min-width:46px;text-align:center;direction:ltr}\n.pe{text-align:center;padding:36px;color:var(--muted);font-size:13px}\n.bi{display:flex;align-items:center;gap:8px;padding:9px 12px;border-bottom:1px solid var(--bdr);direction:ltr}\n.bi:last-child{border-bottom:none}\n.bu{flex:1;font-size:11px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n.bidx{font-size:11px;color:var(--muted);min-width:22px}\n.brm{background:none;border:none;color:var(--accent);cursor:pointer;font-size:15px;padding:0 3px;transition:transform .2s}.brm:hover{transform:scale(1.3)}\n.qi{background:var(--card2);border:1px solid var(--bdr);border-radius:11px;padding:12px 14px;margin-bottom:7px;transition:all .3s}\n.qi.done{background:rgba(0,230,118,.05);border-color:rgba(0,230,118,.25)}\n.qi.err{background:rgba(255,61,61,.05);border-color:rgba(255,61,61,.25)}\n.qt{display:flex;align-items:flex-start;gap:9px;margin-bottom:8px}\n.qico{font-size:17px;flex-shrink:0}\n.qtit{flex:1;font-size:12px;font-weight:600;direction:rtl;text-align:right}\n.qspd{font-size:10px;color:var(--muted);margin-top:3px;direction:ltr;text-align:right}\n.qp{height:4px;background:var(--panel);border-radius:3px;overflow:hidden;margin-bottom:5px}\n.qpi{height:100%;width:0%;border-radius:3px;background:linear-gradient(90deg,var(--green),var(--blue));transition:width .4s}\n.qpi.err{background:var(--accent)}\n.qst{font-size:11px;color:var(--muted);text-align:right}\n.qst.done{color:var(--green)}.qst.err{color:var(--accent)}\n.sbar{display:flex;gap:14px;padding:12px 18px;background:var(--panel);border-radius:11px;margin-bottom:14px;border:1px solid var(--bdr);align-items:center}\n.si{text-align:center}.sv{font-size:20px;font-weight:900}\n.sv.r{color:var(--accent)}.sv.o{color:var(--a2)}.sv.g{color:var(--green)}.sv.go{color:var(--gold)}\n.sl{font-size:10px;color:var(--muted)}.sdiv{width:1px;height:28px;background:var(--bdr)}\n.bdg{display:inline-flex;align-items:center;justify-content:center;background:var(--accent);color:#fff;border-radius:20px;font-size:10px;font-weight:700;padding:2px 7px;margin-right:4px}\n.bdg.g{background:var(--gold);color:#000}\n.div{height:1px;background:var(--bdr);margin:10px 0}\n.ld{animation:sp .7s linear infinite;display:inline-block}@keyframes sp{to{transform:rotate(360deg)}}\n.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(16px);background:var(--card2);border:1px solid var(--bdr);border-radius:9px;padding:10px 22px;font-size:13px;font-weight:600;opacity:0;transition:all .3s;z-index:999;pointer-events:none}\n.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}\n.toast.s{border-color:var(--green);color:var(--green)}.toast.e{border-color:var(--accent);color:var(--accent)}\n</style>\n</head>\n<body>\n<div class="app">\n<aside class="sb">\n  <div class="brand">\n    <span class="brand-icon">▶️</span>\n    <div class="brand-name">YT Downloader Pro</div>\n    <div class="brand-sub">محمّل يوتيوب الاحترافي</div>\n  </div>\n  <div class="nl">التنقل</div>\n  <button class="nb active" onclick="sp(\'single\',this)"><span class="ic">🎬</span>فيديو واحد</button>\n  <button class="nb" onclick="sp(\'playlist\',this)"><span class="ic">📋</span>قائمة تشغيل</button>\n  <button class="nb" onclick="sp(\'batch\',this)"><span class="ic">⚡</span>تحميل مجمّع</button>\n  <button class="nb" onclick="sp(\'queue\',this)"><span class="ic">📥</span>الطابور<span class="bdg" id="qBdg" style="display:none;margin-right:auto">0</span></button>\n  <div class="sb-bot">\n    <div class="dir-box">\n      <div class="dir-lbl">مجلد الحفظ</div>\n      <div class="dir-path" id="dirTxt">~/Downloads</div>\n    </div>\n    <button class="btn-dir" onclick="chgDir()">📁 تغيير المجلد</button>\n    <div class="div"></div>\n    <div class="sig">تصميم وتطوير: عمر جمال</div>\n  </div>\n</aside>\n<main class="content">\n<div class="page active" id="page-single">\n  <div class="ph"><div class="pt">🎬 تحميل فيديو واحد</div><div class="ps">أدخل رابط الفيديو وحدد الجودة والصيغة</div></div>\n  <div class="card">\n    <div class="ct">رابط الفيديو</div>\n    <div class="ir">\n      <input class="inp" id="sUrl" type="text" placeholder="https://youtube.com/watch?v=..." onkeydown="if(event.key===\'Enter\')fsi()">\n      <button class="btn br" onclick="fsi()">🔍 جلب المعلومات</button>\n    </div>\n    <div class="ib" id="sInfo">أدخل الرابط واضغط "جلب المعلومات"</div>\n  </div>\n  <div class="card">\n    <div class="ct">خيارات التحميل</div>\n    <div class="or">\n      <span class="ol">الصيغة:</span>\n      <div class="segs" style="flex:1;max-width:300px">\n        <button class="seg active" onclick="setFmt(\'mp4\',this)">MP4 فيديو</button>\n        <button class="seg" onclick="setFmt(\'mp3\',this)">MP3 صوت</button>\n        <button class="seg" onclick="setFmt(\'webm\',this)">WEBM</button>\n      </div>\n      <span class="ol">الجودة:</span>\n      <select id="sQ">\n        <option value="best">أعلى جودة متاحة</option>\n        <option value="2160">4K (2160p)</option>\n        <option value="1440">1440p</option>\n        <option value="1080">1080p</option>\n        <option value="720">720p</option>\n        <option value="480">480p</option>\n        <option value="360">360p</option>\n        <option value="240">240p</option>\n        <option value="144">144p</option>\n      </select>\n    </div>\n    <div class="pw" id="sPW" style="display:none">\n      <div class="po"><div class="pi" id="sBar"></div></div>\n      <div class="ptxt" id="sTxt">جارٍ التحميل...</div>\n    </div>\n    <button class="btn br bfull" onclick="dlSingle()">⬇ تحميل الفيديو</button>\n  </div>\n</div>\n<div class="page" id="page-playlist">\n  <div class="ph"><div class="pt">📋 تحميل قائمة تشغيل</div><div class="ps">استعرض الفيديوهات وحدد ما تريد تحميله</div></div>\n  <div class="card">\n    <div class="ct">رابط قائمة التشغيل</div>\n    <div class="ir">\n      <input class="inp" id="plUrl" type="text" placeholder="https://youtube.com/playlist?list=...">\n      <button class="btn bo" onclick="fpl()">📋 جلب القائمة</button>\n    </div>\n    <div class="or" style="margin-top:12px">\n      <span class="ol">الجودة:</span>\n      <select id="plQ">\n        <option value="best">أعلى جودة متاحة</option>\n        <option value="1080">1080p</option><option value="720">720p</option>\n        <option value="480">480p</option><option value="360">360p</option>\n        <option value="mp3">صوت فقط (MP3)</option>\n      </select>\n    </div>\n  </div>\n  <div class="card">\n    <div class="plc">\n      <button class="btn bgh bsm" onclick="sAll(true)">☑ تحديد الكل</button>\n      <button class="btn bgh bsm" onclick="sAll(false)">☐ إلغاء الكل</button>\n      <span id="plCnt" style="font-size:12px;color:var(--muted);margin-right:auto"></span>\n    </div>\n    <div class="pll" id="plList"><div class="pe">أدخل رابط قائمة التشغيل واضغط "جلب القائمة"</div></div>\n    <div class="pw" id="plPW" style="display:none">\n      <div class="po"><div class="pi" id="plBar" style="background:linear-gradient(90deg,var(--a2),var(--gold))"></div></div>\n      <div class="ptxt" id="plTxt"></div>\n    </div>\n    <button class="btn bo bfull" onclick="dlPl()">⬇ تحميل المحدد</button>\n  </div>\n</div>\n<div class="page" id="page-batch">\n  <div class="ph"><div class="pt">⚡ تحميل مجمّع</div><div class="ps">أضف روابط متعددة وحمّلها دفعة واحدة</div></div>\n  <div class="card">\n    <div class="ct">إضافة روابط</div>\n    <div class="ir">\n      <input class="inp" id="btEnt" type="text" placeholder="https://youtube.com/watch?v=..." onkeydown="if(event.key===\'Enter\')addBt()">\n      <button class="btn bg" onclick="addBt()">+ إضافة</button>\n    </div>\n    <div class="or" style="margin-top:12px">\n      <span class="ol">الجودة:</span>\n      <select id="btQ">\n        <option value="best">أعلى جودة متاحة</option>\n        <option value="1080">1080p</option><option value="720">720p</option>\n        <option value="480">480p</option><option value="360">360p</option>\n        <option value="mp3">صوت فقط (MP3)</option>\n      </select>\n      <button class="btn bgh bsm" style="margin-right:auto;color:var(--accent)" onclick="clrBt()">🗑 مسح الكل</button>\n      <span class="bdg g" id="btCnt">0</span>\n    </div>\n  </div>\n  <div class="card">\n    <div class="ct">قائمة الروابط</div>\n    <div id="btList"><div class="pe">لم تُضف أي روابط بعد</div></div>\n    <div class="pw" id="btPW" style="display:none">\n      <div class="po"><div class="pi" id="btBar" style="background:linear-gradient(90deg,var(--gold),var(--a2))"></div></div>\n      <div class="ptxt" id="btTxt"></div>\n    </div>\n    <button class="btn bg bfull" onclick="dlBt()">⬇ تحميل الكل</button>\n  </div>\n</div>\n<div class="page" id="page-queue">\n  <div class="ph"><div class="pt">📥 طابور التحميل</div><div class="ps">متابعة تقدم جميع عمليات التحميل</div></div>\n  <div class="sbar">\n    <div class="si"><div class="sv r" id="stT">0</div><div class="sl">المجموع</div></div>\n    <div class="sdiv"></div>\n    <div class="si"><div class="sv o" id="stA">0</div><div class="sl">نشط</div></div>\n    <div class="sdiv"></div>\n    <div class="si"><div class="sv g" id="stD">0</div><div class="sl">مكتمل</div></div>\n    <div class="sdiv"></div>\n    <div class="si"><div class="sv go" id="stE">0</div><div class="sl">خطأ</div></div>\n    <div style="margin-right:auto"><button class="btn bgh bsm" onclick="clrDone()">🧹 مسح المكتملة</button></div>\n  </div>\n  <div id="qList"><div class="pe" id="qEmp">الطابور فارغ — ابدأ التحميل من أحد التبويبات</div></div>\n</div>\n</main>\n</div>\n<div class="toast" id="toast"></div>\n<script>\nvar dlDir=\'~/Downloads\',bUrls=[],plEnt=[],selFmt=\'mp4\',qItems={};\nfunction sp(n,b){document.querySelectorAll(\'.page\').forEach(p=>p.classList.remove(\'active\'));document.querySelectorAll(\'.nb\').forEach(x=>x.classList.remove(\'active\'));document.getElementById(\'page-\'+n).classList.add(\'active\');if(b)b.classList.add(\'active\')}\nfunction setFmt(f,b){selFmt=f;document.querySelectorAll(\'.seg\').forEach(s=>s.classList.remove(\'active\'));b.classList.add(\'active\')}\nfunction toast(m,t){var e=document.getElementById(\'toast\');if(!t)t=\'s\';e.textContent=m;e.className=\'toast \'+t+\' show\';setTimeout(function(){e.classList.remove(\'show\')},2800)}\nfunction chgDir(){var d=prompt(\'أدخل مسار مجلد الحفظ:\',dlDir);if(d){dlDir=d;document.getElementById(\'dirTxt\').textContent=d;fetch(\'/set_dir\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({dir:d})})}}\nasync function fsi(){var url=document.getElementById(\'sUrl\').value.trim();if(!url){toast(\'أدخل الرابط أولاً\',\'e\');return}var b=document.getElementById(\'sInfo\');b.className=\'ib\';b.innerHTML=\'جارٍ جلب معلومات الفيديو...\';try{var r=await fetch(\'/info\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({url:url})});var d=await r.json();if(d.error){b.innerHTML=\'❌ \'+d.error;return}b.className=\'ib loaded\';var dur=fmtD(d.duration),views=d.view_count?Number(d.view_count).toLocaleString():\'—\';b.innerHTML=\'<div><strong>\'+esc(d.title)+\'</strong><br><span style="color:var(--muted);font-size:12px">⏱ \'+dur+\' • 👁 \'+views+\' • 👤 \'+esc(d.uploader||\'—\')+\'</span></div>\'}catch(e){b.innerHTML=\'❌ تعذّر الاتصال\'}}\nasync function dlSingle(){var url=document.getElementById(\'sUrl\').value.trim(),q=document.getElementById(\'sQ\').value;if(!url){toast(\'أدخل الرابط أولاً\',\'e\');return}var pw=document.getElementById(\'sPW\'),bar=document.getElementById(\'sBar\'),txt=document.getElementById(\'sTxt\');pw.style.display=\'block\';bar.style.width=\'0%\';txt.textContent=\'جارٍ التحميل...\';var r=await fetch(\'/download\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({url:url,quality:q,format:selFmt})});var d=await r.json();if(d.error){toast(d.error,\'e\');return}addQI(d.id,url,null);pollDl(d.id,function(p,s,inf){bar.style.width=p+\'%\';txt.textContent=inf;if(s===\'done\'){txt.textContent=\'✅ تم التحميل بنجاح!\';toast(\'✅ تم التحميل بنجاح\')}if(s===\'error\'){txt.textContent=\'❌ \'+inf;toast(\'❌ فشل التحميل\',\'e\')}})}\nasync function fpl(){var url=document.getElementById(\'plUrl\').value.trim();if(!url){toast(\'أدخل الرابط\',\'e\');return}var list=document.getElementById(\'plList\');list.innerHTML=\'<div class="pe">جارٍ جلب القائمة...</div>\';plEnt=[];var r=await fetch(\'/playlist_info\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({url:url})});var d=await r.json();if(d.error){list.innerHTML=\'<div class="pe" style="color:var(--accent)">❌ \'+esc(d.error)+\'</div>\';return}plEnt=d.entries;list.innerHTML=d.entries.map(function(e,i){return\'<div class="pli"><input type="checkbox" id="plc\'+i+\'" checked><span class="pn">\'+(i+1)+\'</span><span class="ptit">\'+esc(e.title||\'بدون عنوان\')+\'</span><span class="pdur">\'+fmtD(e.duration)+\'</span></div>\'}).join(\'\');document.getElementById(\'plCnt\').textContent=\'إجمالي الفيديوهات: \'+d.entries.length}\nfunction sAll(v){document.querySelectorAll(\'#plList input[type=checkbox]\').forEach(function(c){c.checked=v})}\nasync function dlPl(){var sel=plEnt.filter(function(_,i){var c=document.getElementById(\'plc\'+i);return c&&c.checked});if(!sel.length){toast(\'لم تحدد أي فيديوهات\',\'e\');return}var q=document.getElementById(\'plQ\').value,pw=document.getElementById(\'plPW\'),bar=document.getElementById(\'plBar\'),txt=document.getElementById(\'plTxt\'),done=0,total=sel.length;pw.style.display=\'block\';for(var i=0;i<sel.length;i++){var e=sel[i],vurl=e.url||e.webpage_url;if(!vurl)continue;txt.textContent=\'جارٍ تحميل: \'+esc(e.title||vurl);var r=await fetch(\'/download\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({url:vurl,quality:q,format:q===\'mp3\'?\'mp3\':\'mp4\'})});var d=await r.json();if(d.id){addQI(d.id,vurl,e.title);await waitDl(d.id)}done++;bar.style.width=(done/total*100)+\'%\';txt.textContent=\'مكتمل: \'+done+\' / \'+total}toast(\'✅ تم تحميل \'+done+\' فيديوهات\');spN(\'queue\')}\nfunction addBt(){var inp=document.getElementById(\'btEnt\'),url=inp.value.trim();if(!url||!url.startsWith(\'http\')){toast(\'أدخل رابطاً صحيحاً\',\'e\');return}bUrls.push(url);inp.value=\'\';rBt()}\nfunction rBt(){var list=document.getElementById(\'btList\');document.getElementById(\'btCnt\').textContent=bUrls.length;if(!bUrls.length){list.innerHTML=\'<div class="pe">لم تُضف أي روابط بعد</div>\';return}list.innerHTML=bUrls.map(function(u,i){return\'<div class="bi"><button class="brm" onclick="rmBt(\'+i+\')">✕</button><span class="bidx">\'+(i+1)+\'</span><span class="bu">\'+esc(u)+\'</span></div>\'}).join(\'\')}\nfunction rmBt(i){bUrls.splice(i,1);rBt()}function clrBt(){bUrls=[];rBt()}\nasync function dlBt(){if(!bUrls.length){toast(\'لا توجد روابط\',\'e\');return}var q=document.getElementById(\'btQ\').value,pw=document.getElementById(\'btPW\'),bar=document.getElementById(\'btBar\'),txt=document.getElementById(\'btTxt\'),done=0,total=bUrls.length;pw.style.display=\'block\';for(var i=0;i<bUrls.length;i++){var url=bUrls[i];var r=await fetch(\'/download\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({url:url,quality:q,format:q===\'mp3\'?\'mp3\':\'mp4\'})});var d=await r.json();if(d.id){addQI(d.id,url,null);await waitDl(d.id)}done++;bar.style.width=(done/total*100)+\'%\';txt.textContent=\'مكتمل: \'+done+\' / \'+total}toast(\'✅ تم تحميل \'+done+\' روابط\');spN(\'queue\')}\nfunction addQI(id,url,title){qItems[id]={id:id,url:url,title:title||url.slice(-40),status:\'pending\',progress:0};document.getElementById(\'qEmp\').style.display=\'none\';var el=document.createElement(\'div\');el.id=\'qi-\'+id;el.className=\'qi\';el.innerHTML=\'<div class="qt"><span class="qico" id="qic-\'+id+\'">⏳</span><div style="flex:1"><div class="qtit" id="qtt-\'+id+\'">\'+esc(title||url.slice(-40))+\'</div><div class="qspd" id="qsp-\'+id+\'"></div></div></div><div class="qp"><div class="qpi" id="qb-\'+id+\'"></div></div><div class="qst" id="qst-\'+id+\'">في الانتظار...</div>\';document.getElementById(\'qList\').appendChild(el);upStats()}\nfunction upQI(id){var it=qItems[id];if(!it)return;var bar=document.getElementById(\'qb-\'+id),ico=document.getElementById(\'qic-\'+id),tit=document.getElementById(\'qtt-\'+id),spd=document.getElementById(\'qsp-\'+id),st=document.getElementById(\'qst-\'+id),el=document.getElementById(\'qi-\'+id);if(tit&&it.title)tit.textContent=it.title;if(bar)bar.style.width=it.progress+\'%\';if(it.status===\'done\'){if(ico)ico.textContent=\'✅\';if(bar){bar.style.width=\'100%\';bar.classList.remove(\'err\')}if(st){st.textContent=\'✅ تم التحميل بنجاح\';st.className=\'qst done\'}if(el){el.classList.add(\'done\');el.classList.remove(\'err\')}if(spd)spd.textContent=\'\'}else if(it.status===\'error\'){if(ico)ico.textContent=\'❌\';if(bar)bar.classList.add(\'err\');if(st){st.textContent=\'❌ \'+(it.error||\'فشل التحميل\');st.className=\'qst err\'}if(el){el.classList.add(\'err\');el.classList.remove(\'done\')}}else if(it.status===\'downloading\'){if(ico)ico.textContent=\'⬇\';var s=\'\';if(it.speed)s+=\'السرعة: \'+it.speed;if(it.eta)s+=(s?\' • \':\'\')+\' المتبقي: \'+it.eta;if(spd)spd.textContent=s;if(st){st.textContent=(it.progress||0).toFixed(0)+\'%\';st.className=\'qst\'}}}\nfunction pollDl(id,cb){var tmr=setInterval(async function(){var r=await fetch(\'/status/\'+id);var d=await r.json();if(!d.id){clearInterval(tmr);return}Object.assign(qItems[id],d);upQI(id);upStats();var inf=d.speed?\'⬇ \'+(d.progress||0).toFixed(0)+\'%  •  \'+d.speed:\'⬇ \'+(d.progress||0).toFixed(0)+\'%\';if(cb)cb(d.progress||0,d.status,inf);if(d.status===\'done\'||d.status===\'error\'){clearInterval(tmr);if(cb)cb(d.progress||100,d.status,d.status===\'done\'?\'✅ تم التحميل\':\'❌ فشل\')}},800)}\nfunction waitDl(id){return new Promise(function(res){pollDl(id,function(p,s){if(s===\'done\'||s===\'error\')res()})})}\nfunction upStats(){var items=Object.values(qItems),tot=items.length,act=items.filter(function(i){return i.status===\'downloading\'}).length,done=items.filter(function(i){return i.status===\'done\'}).length,err=items.filter(function(i){return i.status===\'error\'}).length;document.getElementById(\'stT\').textContent=tot;document.getElementById(\'stA\').textContent=act;document.getElementById(\'stD\').textContent=done;document.getElementById(\'stE\').textContent=err;var b=document.getElementById(\'qBdg\');if(act>0){b.style.display=\'\';b.textContent=act}else b.style.display=\'none\'}\nfunction clrDone(){Object.keys(qItems).forEach(function(id){var it=qItems[id];if(it.status===\'done\'||it.status===\'error\'){var el=document.getElementById(\'qi-\'+id);if(el)el.remove();delete qItems[id]}});upStats();if(!Object.keys(qItems).length)document.getElementById(\'qEmp\').style.display=\'\'}\nfunction fmtD(s){if(!s)return\'—\';s=parseInt(s);var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=s%60;if(h)return h+\':\'+String(m).padStart(2,\'0\')+\':\'+String(sec).padStart(2,\'0\');return m+\':\'+String(sec).padStart(2,\'0\')}\nfunction esc(s){return String(s||\'\').replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\')}\nfunction spN(n){document.querySelectorAll(\'.page\').forEach(function(p){p.classList.remove(\'active\')});document.querySelectorAll(\'.nb\').forEach(function(b){b.classList.remove(\'active\')});document.getElementById(\'page-\'+n).classList.add(\'active\');document.querySelectorAll(\'.nb\').forEach(function(b){if(b.getAttribute(\'onclick\')&&b.getAttribute(\'onclick\').indexOf("\'"+n+"\'")>=0)b.classList.add(\'active\')})}\n</script>\n</body>\n</html>'

@app.route("/")
def index():
    return TEMPLATE

@app.route("/set_dir", methods=["POST"])
def set_dir():
    global DOWNLOAD_DIR
    d = request.get_json().get("dir","").strip()
    if d:
        expanded = os.path.expanduser(d)
        if os.path.isdir(expanded):
            DOWNLOAD_DIR = expanded
    return jsonify({"ok": True, "dir": DOWNLOAD_DIR})

@app.route("/info", methods=["POST"])
def get_info():
    url = request.get_json().get("url","").strip()
    if not url:
        return jsonify({"error": "لم يتم توفير رابط"})
    try:
        with yt_dlp.YoutubeDL({**YDL_BASE, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({"title":info.get("title","—"),"duration":info.get("duration",0),
                        "uploader":info.get("uploader","—"),"view_count":info.get("view_count",0)})
    except Exception as e:
        return jsonify({"error": str(e)[:120]})

@app.route("/playlist_info", methods=["POST"])
def playlist_info():
    url = request.get_json().get("url","").strip()
    if not url:
        return jsonify({"error": "لم يتم توفير رابط"})
    try:
        opts = {**YDL_BASE, "extract_flat": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = info.get("entries",[])
        if not entries and info.get("_type")=="video":
            entries = [info]
        result = []
        for e in (entries or []):
            if not e: continue
            vid_url = e.get("url") or e.get("webpage_url") or ""
            if not vid_url.startswith("http"):
                vid_id = e.get("id","")
                if vid_id: vid_url = f"https://www.youtube.com/watch?v={vid_id}"
            result.append({"title":e.get("title","بدون عنوان"),"duration":e.get("duration",0),"url":vid_url})
        return jsonify({"entries":result,"total":len(result)})
    except Exception as e:
        return jsonify({"error": str(e)[:120]})

@app.route("/download", methods=["POST"])
def start_download():
    data = request.get_json()
    url  = data.get("url","").strip()
    if not url:
        return jsonify({"error": "لم يتم توفير رابط"})
    dl_id = str(uuid.uuid4())[:8]
    downloads[dl_id] = {"id":dl_id,"url":url,"status":"pending","progress":0,
                        "speed":"","eta":"","title":"","error":""}
    threading.Thread(target=_run, args=(dl_id,url,data.get("quality","best"),data.get("format","mp4")),daemon=True).start()
    return jsonify({"id": dl_id})

def _build_format(quality, fmt):
    if fmt == "mp3" or quality == "mp3":
        return "bestaudio/best", True
    qmap = {
        "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "2160": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]",
        "1440": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]",
        "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
        "720":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
        "480":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
        "360":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
        "240":  "bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[height<=240]",
        "144":  "bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[height<=144]",
    }
    f = qmap.get(quality, qmap["best"])
    if fmt == "webm":
        f = f.replace("[ext=mp4]","[ext=webm]").replace("[ext=m4a]","[ext=webm]")
    return f, False

def _run(dl_id, url, quality, fmt):
    state = downloads[dl_id]
    state["status"] = "downloading"
    format_str, is_audio = _build_format(quality, fmt)

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate",0)
            dled  = d.get("downloaded_bytes",0)
            state["progress"] = round(dled/total*100,1) if total else 0
            spd = d.get("speed"); eta = d.get("eta")
            state["speed"] = f"{spd/1024/1024:.1f} MB/s" if spd else ""
            state["eta"]   = f"{int(eta)}ث" if eta else ""
            if d.get("info_dict"):
                state["title"] = d["info_dict"].get("title", state["title"])
        elif d["status"] == "finished":
            state["progress"] = 100

    try:
        with yt_dlp.YoutubeDL({**YDL_BASE, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            state["title"] = info.get("title", url[:50])
        opts = {
            **YDL_BASE,
            "format":               format_str,
            "outtmpl":              os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "progress_hooks":       [hook],
            "merge_output_format":  "mp4" if not is_audio else None,
        }
        if is_audio:
            opts["postprocessors"] = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        state["status"] = "done"
        state["progress"] = 100
    except Exception as e:
        state["status"] = "error"
        state["error"]  = str(e)[:150]

@app.route("/status/<dl_id>")
def get_status(dl_id):
    if dl_id not in downloads:
        return jsonify({"error": "not found"}), 404
    return jsonify(downloads[dl_id])

if __name__ == "__main__":
    import webbrowser, time as _t
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print("\n" + "="*52)
    print("  YouTube Downloader Pro")
    print("  تصميم وتطوير: عمر جمال")
    print("="*52)
    print(f"  Browser: http://localhost:5000")
    print(f"  Save folder: {DOWNLOAD_DIR}")
    print("  Stop: Ctrl+C")
    print("="*52 + "\n")
    threading.Thread(target=lambda: (_t.sleep(1.2), webbrowser.open("http://localhost:5000")), daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
