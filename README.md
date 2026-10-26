# Darksham OS

نظام ألعاب عربي مبني على [Bazzite](https://bazzite.gg) (Fedora Atomic / Universal Blue).
الهدف: نظام بتلعب فيه وبتصنع ألعاب فيه، مع Darksham Engine واللانشر والمساعد Ofuq.

## الحالة: 0.1 تجريبي
- [x] لغة عربية افتراضية وخطوط Noto العربية
- [x] اسم النظام Darksham OS
- [x] شعار وخلفية Darksham (بتختارها من إعدادات الخلفية)
- [ ] خلفية افتراضية وشاشة إقلاع
- [ ] Darksham Launcher
- [ ] Darksham Engine مثبّت
- [ ] Ofuq كخدمة محلية

## كيف بينبني
كل دفعة على فرع `main` بتبني الصورة تلقائياً بـGitHub Actions وبترفعها على:
`ghcr.io/tamyyaz/ds-os:latest`

ملفات مهمة:
- `Containerfile`: صورة الأساس (عادي أو NVIDIA)
- `build_files/build.sh`: كل تعديلات النظام
- `system_files/`: ملفات بتنسخ متل ما هي لجذر النظام `/`

## التجربة على جهاز افتراضي
1. ثبّت Bazzite العادي على VirtualBox أو virt-manager (6 GB رام، 50 GB مساحة).
2. بعد التثبيت:
   ```bash
   sudo bootc switch ghcr.io/tamyyaz/ds-os:latest
   ```
3. أعد التشغيل.

## التوقيع (اختياري هلق، ضروري قبل النشر)
البناء بيشتغل بدون توقيع. لتفعيله:
```bash
COSIGN_PASSWORD="" cosign generate-key-pair
```
حط محتوى `cosign.key` بـ Settings ← Secrets ← Actions باسم `SIGNING_SECRET`، وارفع `cosign.pub` للمستودع.
**لا ترفع `cosign.key` أبداً.**

## الترخيص
القالب الأصلي من [ublue-os/image-template](https://github.com/ublue-os/image-template) (Apache-2.0).
