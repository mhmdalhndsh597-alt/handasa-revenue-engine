# Handasa Revenue Engine

محرك تقارير قراءة فقط لتحليل رقم آخر كتلة وإخراج **تقدير توضيحي** اختياري. لا يثبت هذا المشروع ملكية محفظة أو سلطة حوكمة أو استحقاق عوائد، ولا يوقّع أو يرسل أو يحوّل أي معاملة.

## المتغيرات

ضع هذه القيم العامة في GitHub Actions Variables:

- `OBSERVED_VOLUME_USD` — قيمة حجم مراقبة مقدمة من مصدر موثوق؛ لا يدّعي السكربت أنه يستخرج حجم USDT من `eth_blockNumber`.
- `FEE_PERCENTAGE` — نسبة تقديرية للتقارير فقط، مثل `0.005`.

ضع هذه القيم الحساسة في GitHub Actions Secrets:

- `NETWORK_RPC_URL` — رابط RPC للقراءة فقط.
- `DISCORD_WEBHOOK` — Webhook للتقرير الاختياري.

لا تضع مفاتيح خاصة أو عبارات استرداد أو عناوين محافظ حساسة في الكود أو السجلات أو Discord.

## التشغيل

```bash
export NETWORK_RPC_URL="https://your-read-only-rpc.example"
export OBSERVED_VOLUME_USD="0"
export FEE_PERCENTAGE="0.005"
python revenue_engine.py
```

## الأتمتة

يشغّل `.github/workflows/revenue_cron.yml` اختبارات الجودة ثم المحرك كل 5 دقائق أو يدويًا. GitHub Actions قد يؤخر الجدولة قليلًا بسبب ازدحام الخدمة.

## ملاحظة مهمة

النسخة الأصلية المرسلة في الطلب احتوت على بيانات افتراضية وادعاء حوكمة غير قابل للتحقق وعنوان محفظة داخل الكود. تم استبدالها هنا بحساب تقديري معلَّم بوضوح ووضع قراءة فقط.
