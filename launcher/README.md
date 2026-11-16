# Darksham Launcher

مشروع Darksham Engine (Godot 4.4.1 المعدّل). شاشة ألعاب ببطاقات أفقية، عربي أولاً (RTL) مع إنجليزي.

## الحالة (صادقة)
- **شاشة Games**: بطاقات، انعكاس، خلفية بلون اللعبة المحددة، تنقل بالأسهم والجويستيك. انجرّبت على ويندوز (RTX 2080) وطلعت لقطات، واختبار التنقل الآلي نجح (9 من 9).
- **Profile**: أرقام من بيانات المزوّد (تجريبية هلق). **Apps**: "قريباً".
- **المزوّد الوحيد حالياً `MockProvider`**: ألعاب Darksham التجريبية وأغلفة مولّدة بتدرّج لوني. ما في Steam ولا Lutris بعد.
- **ما انجرّب**: لينكس، gamescope، جلسة تسجيل دخول، يد تحكم حقيقية، خطوط Sora وNoto Kufi (بتنزل للخط التالي إذا مو مثبّتة).

## تشغيل
المحرك هو `darksham-engine` (مجلد المحرك، مو بهالمستودع). افتح المشروع بالمحرك: بيضيف الإضافة `addons/` لحاله.

```bash
ENGINE --headless --path launcher --import          # مرة وحدة
ENGINE --path launcher                              # تشغيل
ENGINE --path launcher -- --lang=en --select=3      # خيارات للتجربة: --lang --select --tab
ENGINE --headless --path launcher --script res://tests/nav_test.gd   # اختبار التنقل
```

مفاتيح: أسهم أو D-pad/عصا = تنقل، Enter أو A = تشغيل، Q/E أو الأكتاف = تبديل القسم، F2 أو Y = عربي/إنجليزي.

## الهيكل
- `scripts/library_provider.gd`: واجهة مصدر الألعاب. كل مصدر (Steam، Lutris، Heroic) مزوّد لحاله، والشاشات ما بتعرف من وين اللعبة.
- `scripts/mock_provider.gd`: المزوّد التجريبي.
- `scripts/main.gd`: الشاشات. `scripts/game_card.gd`: البطاقة. `shaders/`: الخلفية والبطاقة والانعكاس.

## الخطوة الجاية
مزوّد Steam: قراءة `libraryfolders.vdf` وملفات `appmanifest_*.acf` وإطلاق بـ`steam -applaunch <id>`. بعده الجلسة (gamescope-session-plus).
