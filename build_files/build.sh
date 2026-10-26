#!/bin/bash
# Darksham OS — build.sh
# كل تعديلات النظام بتصير هون. بيشتغل مرة وحدة وقت بناء الصورة.

set -ouex pipefail

### 0) ملفات النظام الجاهزة (system_files/ بالمستودع ← جذر النظام /)
# فيها: إعدادات الخطوط العربية، ومجلد Darksham
cp -avf "/ctx/system_files"/. /

### 1) العربي: لغة وخطوط
dnf5 install -y \
    glibc-langpack-ar \
    google-noto-kufi-arabic-fonts \
    google-noto-naskh-arabic-fonts \
    google-noto-sans-arabic-fonts

# اللغة الافتراضية عربي (المستخدم بيقدر يغيّرها من الإعدادات أو وقت التثبيت)
echo 'LANG=ar_SY.UTF-8' > /etc/locale.conf

# تحديث ذاكرة الخطوط حتى يلقط إعدادات الخطوط الجديدة
fc-cache -f

### 2) الهوية: اسم النظام
# منغيّر الاسم الظاهر بس، ومنخلّي ID متل ما هو حتى ما تخرب التحديثات وأدوات Bazzite
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="Darksham OS"/' /usr/lib/os-release
if grep -q '^VARIANT=' /usr/lib/os-release; then
    sed -i 's/^VARIANT=.*/VARIANT="Darksham"/' /usr/lib/os-release
else
    echo 'VARIANT="Darksham"' >> /usr/lib/os-release
fi

### 3) الأيقونات: Fluent (رمادي) بشكل قريب من ويندوز 11
# نسخة مثبّتة بتاريخ حتى ما يتغيّر النظام لحالو. الترخيص GPL-3.0
FLUENT_TAG="2026-07-27"
command -v git >/dev/null || dnf5 install -y git
git clone --depth 1 --branch "${FLUENT_TAG}" \
    https://github.com/vinceliuice/Fluent-icon-theme /tmp/fluent-icons
bash /tmp/fluent-icons/install.sh -d /usr/share/icons grey
rm -rf /tmp/fluent-icons
# أيقونات Darksham (زر البدء وأيقونة النظام)
gtk-update-icon-cache -f /usr/share/icons/hicolor || true

### 4) شاشة تسجيل الدخول: خلفية Darksham
for theme in /usr/share/sddm/themes/*breeze*; do
    [ -d "${theme}" ] || continue
    printf '[General]\nbackground=/usr/share/wallpapers/Darksham/contents/images/3840x2160.png\n' \
        > "${theme}/theme.conf.user"
done

### 5) الخدمات
systemctl enable podman.socket
