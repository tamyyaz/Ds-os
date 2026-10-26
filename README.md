# Darksham OS

نظام ألعاب عربي مبني على [Bazzite](https://bazzite.gg) (Fedora Atomic / Universal Blue).
الهدف: نظام بتلعب فيه وبتصنع ألعاب فيه، مع Darksham Engine واللانشر والمساعد Ofuq.

## الحالة: 0.1 تجريبي
- [x] لغة عربية افتراضية وخطوط Noto العربية
- [x] اسم النظام Darksham OS
- [x] شعار وخلفية Darksham (افتراضية للمستخدم الجديد)
- [x] ثيم Darksham: ألوان، أيقونات Fluent، شريط مهام متل ويندوز وزر بدء D
- [x] أنيميشن نوافذ قوية (glide، magic lamp، wobbly، blur)
- [x] شاشة تحميل بعد الدخول فيها أنيميشن الشعار
- [x] خلفية شاشة القفل وشاشة الدخول
- [ ] شاشة الإقلاع (Plymouth)
- [x] ثلاث صور: AMD/Intel وNVIDIA حديث وNVIDIA قديم
- [x] أدوات المطوّر (Docker وVS Code وPodman) من Bazzite-DX
- [ ] برامج Darksham (ترحيب، إعدادات)
- [ ] Darksham Launcher
- [ ] Darksham Engine مثبّت
- [ ] Ofuq كخدمة محلية

## الصور (اختار حسب كرت الشاشة)
| الصورة | القاعدة | لمين |
|---|---|---|
| `ds-os` | Bazzite-DX | كروت AMD وIntel (وجهاز افتراضي) |
| `ds-os-nvidia` | Bazzite-DX NVIDIA | **RTX وGTX 16 وما فوق** (تعريفات NVIDIA المفتوحة) |
| `ds-os-nvidia-legacy` | Bazzite NVIDIA | GTX 10 وأقدم (بدون أدوات المطوّر) |

نسخ DX فيها أدوات المطوّر: Docker وPodman وVS Code وDistrobox.
نسخة الكروت القديمة بدون DX لأن Bazzite ما بيصدر نسخة DX إلها.

## كيف بينبني
كل دفعة على فرع `main` بتبني الصور الثلاث تلقائياً بـGitHub Actions وبترفعها على:
`ghcr.io/tamyyaz/<اسم الصورة>:latest`

ملفات مهمة:
- `Containerfile`: صورة الأساس بتجي كـ`BASE_IMAGE` من الـworkflow
- `.github/workflows/build.yml`: جدول الصور الثلاث
- `build_files/build.sh`: كل تعديلات النظام
- `system_files/`: ملفات بتنسخ متل ما هي لجذر النظام `/`

## التجربة على جهاز افتراضي
1. ثبّت Bazzite العادي على VirtualBox أو virt-manager (6 GB رام، 50 GB مساحة).
2. بعد التثبيت (غيّر الاسم حسب الكرت):
   ```bash
   sudo bootc switch ghcr.io/tamyyaz/ds-os:latest
   ```
3. أعد التشغيل.

> لازم تكون الحزمة عامة: GitHub ← Packages ← اسم الصورة ← Package settings ← Change visibility ← Public.

## التوقيع (اختياري هلق، ضروري قبل النشر)
البناء بيشتغل بدون توقيع. لتفعيله:
```bash
COSIGN_PASSWORD="" cosign generate-key-pair
```
حط محتوى `cosign.key` بـ Settings ← Secrets ← Actions باسم `SIGNING_SECRET`، وارفع `cosign.pub` للمستودع.
**لا ترفع `cosign.key` أبداً.**

## الترخيص
القالب الأصلي من [ublue-os/image-template](https://github.com/ublue-os/image-template) (Apache-2.0).
