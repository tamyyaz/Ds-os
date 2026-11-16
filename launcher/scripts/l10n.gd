class_name L10n
extends RefCounted
## Two languages, Arabic (RTL) is the default.

const T := {
	"ar": {
		"games": "الألعاب", "profile": "الملف الشخصي", "apps": "التطبيقات",
		"play": "تشغيل", "switch_tab": "تبديل القسم", "move": "تنقّل", "lang": "EN",
		"soon": "قريباً", "apps_soon": "التطبيقات قادمة في نسخة لاحقة",
		"player": "لاعب Darksham", "stat_games": "عدد الألعاب", "stat_hours": "ساعات اللعب",
		"hours": "ساعة", "last": "آخر لعب", "today": "اليوم", "yesterday": "أمس", "never": "لم تُلعب بعد",
		"demo_launch": "نسخة تجريبية: لن تُشغَّل «%s» فعلاً",
		"src_darksham": "Darksham", "src_steam": "Steam",
	},
	"en": {
		"games": "Games", "profile": "Profile", "apps": "Apps",
		"play": "Play", "switch_tab": "Switch tab", "move": "Move", "lang": "عربي",
		"soon": "Coming soon", "apps_soon": "Apps arrive in a later version",
		"player": "Darksham player", "stat_games": "Games", "stat_hours": "Hours played",
		"hours": "h", "last": "Last played", "today": "Today", "yesterday": "Yesterday", "never": "Never played",
		"demo_launch": "Demo build: \"%s\" will not really start",
		"src_darksham": "Darksham", "src_steam": "Steam",
	},
}

static var lang := "ar"


static func t(key: String) -> String:
	return T[lang].get(key, key)


static func is_rtl() -> bool:
	return lang == "ar"


static func toggle() -> void:
	lang = "en" if lang == "ar" else "ar"
