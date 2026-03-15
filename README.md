# YouTube Downloader Pro
### تصميم وتطوير: عمر جمال

---

## الرفع على Railway (الأسرع والأسهل — مجاني)

### الخطوات:

**1. اعمل حساب على railway.app**
- روح على https://railway.app وسجّل بحساب GitHub

**2. ارفع الملفات على GitHub**
- اعمل repo جديد على github.com
- ارفع الملفات الأربعة: `app.py`, `requirements.txt`, `Procfile`, `railway.toml`

**3. اربط Railway بالـ repo**
- من Railway dashboard → New Project → Deploy from GitHub repo
- اختار الـ repo → بيبني ويشغّل تلقائياً

**4. احصل على الرابط**
- من Settings → Domains → Generate Domain
- هتاخد رابط زي: `https://yt-downloader-xxx.up.railway.app`

---

## الرفع على Render (بديل مجاني)

1. روح على https://render.com وسجّل
2. New → Web Service → ربطه بالـ GitHub repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --workers 1 --threads 8 --timeout 600`
5. اضغط Deploy

---

## التشغيل المحلي (على جهازك)

```bash
pip install flask yt-dlp gunicorn
python app.py
```

ثم افتح: http://localhost:5000

---

## ملاحظات مهمة

- الملفات بتتحذف تلقائياً بعد التحميل (لتوفير المساحة)
- الخطأ SSL/DECRYPTION محلول بـ `"http2": False`
- الـ Free tier على Railway/Render فيه حد 512MB RAM — كافي لـ 2-3 مستخدمين في نفس الوقت
- لو محتاج سعة أكبر → Render Starter plan ($7/شهر)

---

## هيكل الملفات

```
yt-downloader/
├── app.py            ← البرنامج الرئيسي
├── requirements.txt  ← المكتبات
├── Procfile          ← تعليمات التشغيل
└── railway.toml      ← إعدادات Railway
```
