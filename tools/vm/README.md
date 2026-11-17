# تجربة Darksham OS على جهاز افتراضي (Hyper-V)

الصورة (`ghcr.io/tamyyaz/ds-os`) هي صورة bootc، فأسهل طريقة للتجربة: بتثبّت **Bazzite** عادي بالـVM وبعدين بتحوّله لـDarksham بأمر واحد.

## قبل ما تبدأ
- **ويندوز Pro/Enterprise مع Hyper-V.** (جهازك: Windows 11 Pro، والوحدة موجودة. إذا لأ شغّل السكربت مرة بـ`-EnableHyperV` وأعد التشغيل.)
- **ISO لـBazzite** (KDE، AMD/Intel) من https://bazzite.gg (الـ"image picker"). حجمه عدة GB، وأنت اللي بتنزّله: السكربت ما بينزّل شي.
- **مساحة**: 45GB فاضية على الأقل. السكربت بيختار الدرايف الأكبر مساحة لحاله (على جهازك طلع `D:\VMs`).
- **حزمة GHCR لازم تكون Public** (GitHub ← Packages ← `ds-os` ← Package settings ← Change visibility)، وإلا `bootc switch` ما بيقدر يسحب الصورة. إذا ما بدك تخلّيها Public: بالـVM اعمل `sudo podman login ghcr.io -u tamyyaz --authfile /etc/ostree/auth.json` وحط توكن بصلاحية `read:packages` (**لا تبعت التوكن بأي محادثة**).

## الخطوات
```powershell
cd "C:\Users\Snap\Desktop\darksham os\tools\vm"
.\New-DarkshamVM.ps1 -IsoPath D:\ISOs\bazzite-stable-amd64.iso -DryRun     # بس بيطبع الخطة
.\New-DarkshamVM.ps1 -IsoPath D:\ISOs\bazzite-stable-amd64.iso              # بينشئ الـVM ويشغّلها (بيطلب صلاحية أدمن)
```
1. ثبّت Bazzite بنافذة الـVM (اختار القرص، اعمل مستخدم). **لما يطلب إعادة تشغيل، سكّر الـVM** وبعدين:
   ```powershell
   .\New-DarkshamVM.ps1 -EjectIso      # بيشيل الـISO وبيقلّع من القرص
   ```
2. سجّل دخول، افتح Terminal، وحوّل لـDarksham OS:
   ```bash
   sudo bootc switch ghcr.io/tamyyaz/ds-os:latest && systemctl reboot
   ```
3. بعد إعادة التشغيل، افحص:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/tamyyaz/Ds-os/main/tools/vm/vm-check.sh | bash
   ```
   بيطلع تقرير PASS/WARN/FAIL وبيتخزّن بـ`~/darksham-vm-report.txt`. ابعتلي التقرير + لقطات للشاشة (سطح المكتب، شاشة الدخول، اللانشر: افتح "Darksham Launcher" من القائمة).
4. للحذف: `.\New-DarkshamVM.ps1 -Remove`.

## شو بيغطي وشو لأ (صدق)
| بيغطي | ما بيغطي |
|---|---|
| الإقلاع، `bootc switch`، الثيم، السبلاش، شاشة الدخول، اللغة والخطوط | **Gaming Mode / gamescope** (Hyper-V ما بيعطي لينكس تسريع 3D) |
| اللانشر بنافذة (Chromium + الـbackend)، واجهته وحركاته (أبطأ لأن الرسم برمجي) | تعريفات NVIDIA، أداء الألعاب، يد التحكم |
| وجود الحزم والملفات اللي ضفتها بالصورة | تشغيل لعبة فعلي (بدو Steam وحساب) |

للأشياء اللي بالعمود التاني لازم جهاز حقيقي (ممكن USB بنفس الـISO + `bootc switch`).

## ملاحظات عن السكربت
- **ما بيلمس VMs موجودة**: بيرفض لو الاسم مستخدم، و`-Remove` بيطلب تكتب `YES`.
- **الإعدادات**: جيل 2، Secure Boot بقالب Microsoft UEFI CA (اللي بيقلّع لينكس)، ذاكرة ثابتة، نقاط الاستعادة (checkpoints) مطفية، دقة 1920×1080.
- **انجرّب** (ويندوز 11 Pro): قراءة الأخطاء، `-DryRun`، فحص ISO صغير، فحص الذاكرة، واختيار الدرايف. **ما انجرّب إنشاء VM فعلي** (بدو موافقة أدمن UAC على جهازك)، ولا تثبيت Bazzite ولا `bootc switch`.
- `vm-check.sh` انجرّب على جذر وهمي مبني من ملفات المستودع (الفحوص اللي بتعتمد على `build.sh` طلعت FAIL كما هو متوقع هناك). **ما انجرّب على لينكس حقيقي.**
