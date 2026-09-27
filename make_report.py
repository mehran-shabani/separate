from pathlib import Path
import json, html
root=Path(__file__).resolve().parent
out=root/'output'
summary='''نتیجهٔ بررسی صدای 01012007.3gp

وضعیت: خروجی آزمایشی جداسازی و کاهش نویز ساخته شد. جداسازی قطعی آقا و خانم و متن قابل اعتماد گفتگو تأیید نشده است.

مشخصات: ۳۱٫۳۴ ثانیه، تک‌کاناله، AMR-NB، نرخ نمونه‌برداری اصلی ۸۰۰۰ هرتز.
فایل اصلی ویدیو تغییر نکرده است. افزایش نرخ خروجی به ۱۶۰۰۰ هرتز، جزئیات ازدست‌رفته ضبط را برنمی‌گرداند.

فایل‌ها:
01_original.wav: صدای استخراج‌شده بدون فیلتر.
02_cleaned.wav: کل صدا با کاهش ملایم نویز و تنظیم بلندی.
03_speaker_1.wav و 04_speaker_2.wav: دو خروجی تخمینی مدل جداسازی.
speaker_1_cleaned.wav و speaker_2_cleaned.wav: خروجی‌های جداشده با کاهش نویز اضافی.
فایل‌های boosted: تقویت بخش‌های کم‌صدا؛ ممکن است نویز و آثار پردازش هم بلندتر شوند.

متن گفتگو:
گویندهٔ ۱: [متن قابل اعتماد استخراج نشد]
گویندهٔ ۲: [متن قابل اعتماد استخراج نشد]
این نتیجه به معنی نبودن گفتار یا نامفهوم بودن قطعی آن برای شنوندهٔ انسانی نیست.
نام‌گذاری ۱ و ۲ فقط شمارهٔ خروجی مدل است. تعلق کامل هر خروجی به یک نفر و تطبیق آقا/خانم تأیید نشده است؛ نشت صدا و جابه‌جایی گوینده ممکن است.
امکان بازشنوی مستقیم صوت توسط دستیار در این محیط فراهم نبود؛ ارزیابی انجام‌شده ماشینی و فنی است، نه تأیید شنیداری انسانی.

روش:
استخراج با FFmpeg؛ کاهش نویز طیفی ملایم؛ جداسازی با SpeechBrain SepFormer WHAMR در پنجره‌های ۱۰ ثانیه‌ای با هم‌پوشانی ۴ ثانیه و تطبیق همبستگی برای کاهش جابه‌جایی کانال‌ها؛ بازشناسی فارسی با faster-whisper large-v3-turbo و small.
خروجی‌های بازشناسی تکراری یا ناسازگار تأیید نشده‌اند و نباید به افراد نسبت داده شوند. فایل‌های *_asr.json صرفاً خروجی خام و تأییدنشدهٔ مدل هستند.
پردازش صوت محلی انجام شد؛ برای دریافت مدل‌ها از اینترنت استفاده شد.

منابع مدل و ابزار:
https://huggingface.co/speechbrain/sepformer-whamr
https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo
https://huggingface.co/Systran/faster-whisper-small
https://github.com/SYSTRAN/faster-whisper
'''
(out/'README_FA.txt').write_text(summary,encoding='utf-8-sig')
tracks=[('صدای اصلی','01_original.wav'),('کل صدا با کاهش نویز','02_cleaned.wav'),('خروجی جداسازی ۱ — هویت گوینده تأیید نشده','speaker_1_cleaned.wav'),('خروجی جداسازی ۲ — هویت گوینده تأیید نشده','speaker_2_cleaned.wav'),('خروجی ۱ با تقویت بخش‌های کم‌صدا','speaker_1_cleaned_boosted.wav'),('خروجی ۲ با تقویت بخش‌های کم‌صدا','speaker_2_cleaned_boosted.wav'),('صدای اصلی با تقویت بخش‌های کم‌صدا','01_original_boosted.wav')]
cards=''.join(f'<section><h2>{title}</h2><audio controls preload="metadata" src="{name}"></audio><p><a href="{name}" download>دریافت WAV</a></p></section>' for title,name in tracks)
page='''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>بررسی صدای ضبط قدیمی</title><style>body{font-family:Tahoma,Arial,sans-serif;background:#f4f6f8;color:#172232;max-width:860px;margin:40px auto;padding:0 20px;line-height:1.9}h1{font-size:26px}h2{font-size:18px}section,.notice{background:white;padding:18px 24px;margin:18px 0;border:1px solid #dce2e8;border-radius:12px}audio{width:100%}a{color:#125db0}button,select{padding:8px;font-size:16px}.notice{border-right:5px solid #d1982e}pre{white-space:pre-wrap;font:14px Tahoma;line-height:2}small{color:#4a5666}</style><h1>بررسی صدای ضبط قدیمی</h1><p>۳۱٫۳۴ ثانیه • ضبط تک‌کاناله AMR • نسخهٔ آزمایشی پردازش</p><div class="notice"><strong>متن قابل اعتماد گفتگو به دست نیامد.</strong><p>دو فایل زیر خروجی تخمینی مدل‌اند. جداسازی کامل افراد، حذف کامل نویز و تطبیق آقا/خانم تأیید نشده است. خروجی بازشناسی ماشینی را نباید نقل‌قول واقعی دانست.</p></div><label>سرعت پخش: <select id="speed"><option value="1">عادی</option><option value="0.85">۰٫۸۵</option><option value="0.7">۰٫۷</option></select></label>'''+cards+'''<details><summary>روش کار و محدودیت‌های بررسی</summary><pre>'''+html.escape(summary)+'''</pre></details><script>const players=[...document.querySelectorAll('audio')];document.getElementById('speed').onchange=e=>players.forEach(a=>{a.playbackRate=+e.target.value;a.preservesPitch=true});players.forEach(a=>a.onplay=()=>players.filter(b=>b!==a).forEach(b=>b.pause()));</script></html>'''
(out/'review.html').write_text(page,encoding='utf-8')
print('Report created:',out/'review.html')
