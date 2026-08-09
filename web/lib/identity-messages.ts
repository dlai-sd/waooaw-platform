// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-01–06
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import type { SupportedLocale } from './preferences';

const en = {
  eyebrow: 'Secure registration', title: 'Create your WAOOAW account', description: 'Your identity is verified through WAOOAW’s approved broker before an account is completed.',
  displayName: 'Your name', businessName: 'Business name', businessDomain: 'Type of business', email: 'Email address', mobile: 'Mobile number', code: 'Six-digit code',
  saveProfile: 'Save and continue', sendCode: 'Send verification code', verifyCode: 'Verify code', complete: 'Complete registration', optionalMobile: 'Verify mobile now',
  working: 'Securing your registration…', retry: 'Try again', signInFirst: 'Continue securely to create your account', signInDescription: 'WAOOAW uses Keycloak to broker approved sign-in methods. Your access token is never exposed to this page.',
  verificationSent: 'Enter the code sent to', unavailable: 'Registration could not be completed. No account change was assumed.', duplicate: 'Additional identity confirmation is required before this account can be completed.',
} as const;

export type IdentityMessages = { [Key in keyof typeof en]: string };

const translations: Partial<Record<SupportedLocale, Partial<IdentityMessages>>> = {
  hi: { title: 'अपना WAOOAW खाता बनाएँ', displayName: 'आपका नाम', businessName: 'व्यवसाय का नाम', businessDomain: 'व्यवसाय का प्रकार', email: 'ईमेल पता', mobile: 'मोबाइल नंबर', code: 'छह अंकों का कोड', saveProfile: 'सहेजें और जारी रखें', sendCode: 'सत्यापन कोड भेजें', verifyCode: 'कोड सत्यापित करें', complete: 'पंजीकरण पूरा करें', retry: 'फिर प्रयास करें' },
  mr: { title: 'तुमचे WAOOAW खाते तयार करा', displayName: 'तुमचे नाव', businessName: 'व्यवसायाचे नाव', businessDomain: 'व्यवसायाचा प्रकार', email: 'ईमेल पत्ता', mobile: 'मोबाइल क्रमांक', code: 'सहा अंकी कोड', saveProfile: 'जतन करून पुढे जा', sendCode: 'पडताळणी कोड पाठवा', verifyCode: 'कोड पडताळा', complete: 'नोंदणी पूर्ण करा', retry: 'पुन्हा प्रयत्न करा' },
  ta: { title: 'உங்கள் WAOOAW கணக்கை உருவாக்குங்கள்', displayName: 'உங்கள் பெயர்', businessName: 'வணிகப் பெயர்', businessDomain: 'வணிக வகை', email: 'மின்னஞ்சல் முகவரி', mobile: 'கைபேசி எண்', code: 'ஆறு இலக்கக் குறியீடு', saveProfile: 'சேமித்து தொடரவும்', sendCode: 'சரிபார்ப்புக் குறியீட்டை அனுப்பவும்', verifyCode: 'குறியீட்டைச் சரிபார்க்கவும்', complete: 'பதிவை முடிக்கவும்', retry: 'மீண்டும் முயலவும்' },
  te: { title: 'మీ WAOOAW ఖాతాను సృష్టించండి', displayName: 'మీ పేరు', businessName: 'వ్యాపార పేరు', businessDomain: 'వ్యాపార రకం', email: 'ఈమెయిల్ చిరునామా', mobile: 'మొబైల్ నంబర్', code: 'ఆరు అంకెల కోడ్', saveProfile: 'సేవ్ చేసి కొనసాగండి', sendCode: 'ధృవీకరణ కోడ్ పంపండి', verifyCode: 'కోడ్‌ను ధృవీకరించండి', complete: 'నమోదు పూర్తి చేయండి', retry: 'మళ్లీ ప్రయత్నించండి' },
  kn: { title: 'ನಿಮ್ಮ WAOOAW ಖಾತೆಯನ್ನು ರಚಿಸಿ', displayName: 'ನಿಮ್ಮ ಹೆಸರು', businessName: 'ವ್ಯವಹಾರದ ಹೆಸರು', businessDomain: 'ವ್ಯವಹಾರದ ಪ್ರಕಾರ', email: 'ಇಮೇಲ್ ವಿಳಾಸ', mobile: 'ಮೊಬೈಲ್ ಸಂಖ್ಯೆ', code: 'ಆರು ಅಂಕಿಯ ಕೋಡ್', saveProfile: 'ಉಳಿಸಿ ಮುಂದುವರಿಯಿರಿ', sendCode: 'ಪರಿಶೀಲನಾ ಕೋಡ್ ಕಳುಹಿಸಿ', verifyCode: 'ಕೋಡ್ ಪರಿಶೀಲಿಸಿ', complete: 'ನೋಂದಣಿ ಪೂರ್ಣಗೊಳಿಸಿ', retry: 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ' },
  gu: { title: 'તમારું WAOOAW ખાતું બનાવો', displayName: 'તમારું નામ', businessName: 'વ્યવસાયનું નામ', businessDomain: 'વ્યવસાયનો પ્રકાર', email: 'ઈમેલ સરનામું', mobile: 'મોબાઇલ નંબર', code: 'છ અંકનો કોડ', saveProfile: 'સાચવો અને આગળ વધો', sendCode: 'ચકાસણી કોડ મોકલો', verifyCode: 'કોડ ચકાસો', complete: 'નોંધણી પૂર્ણ કરો', retry: 'ફરી પ્રયાસ કરો' },
  bn: { title: 'আপনার WAOOAW অ্যাকাউন্ট তৈরি করুন', displayName: 'আপনার নাম', businessName: 'ব্যবসার নাম', businessDomain: 'ব্যবসার ধরন', email: 'ইমেইল ঠিকানা', mobile: 'মোবাইল নম্বর', code: 'ছয় সংখ্যার কোড', saveProfile: 'সংরক্ষণ করে এগিয়ে যান', sendCode: 'যাচাইকরণ কোড পাঠান', verifyCode: 'কোড যাচাই করুন', complete: 'নিবন্ধন সম্পূর্ণ করুন', retry: 'আবার চেষ্টা করুন' },
  ml: { title: 'നിങ്ങളുടെ WAOOAW അക്കൗണ്ട് സൃഷ്ടിക്കുക', displayName: 'നിങ്ങളുടെ പേര്', businessName: 'ബിസിനസിന്റെ പേര്', businessDomain: 'ബിസിനസിന്റെ തരം', email: 'ഇമെയിൽ വിലാസം', mobile: 'മൊബൈൽ നമ്പർ', code: 'ആറക്ക കോഡ്', saveProfile: 'സംരക്ഷിച്ച് തുടരുക', sendCode: 'സ്ഥിരീകരണ കോഡ് അയയ്ക്കുക', verifyCode: 'കോഡ് സ്ഥിരീകരിക്കുക', complete: 'രജിസ്ട്രേഷൻ പൂർത്തിയാക്കുക', retry: 'വീണ്ടും ശ്രമിക്കുക' },
  pa: { title: 'ਆਪਣਾ WAOOAW ਖਾਤਾ ਬਣਾਓ', displayName: 'ਤੁਹਾਡਾ ਨਾਮ', businessName: 'ਕਾਰੋਬਾਰ ਦਾ ਨਾਮ', businessDomain: 'ਕਾਰੋਬਾਰ ਦੀ ਕਿਸਮ', email: 'ਈਮੇਲ ਪਤਾ', mobile: 'ਮੋਬਾਈਲ ਨੰਬਰ', code: 'ਛੇ ਅੰਕਾਂ ਦਾ ਕੋਡ', saveProfile: 'ਸੰਭਾਲੋ ਅਤੇ ਅੱਗੇ ਵਧੋ', sendCode: 'ਤਸਦੀਕ ਕੋਡ ਭੇਜੋ', verifyCode: 'ਕੋਡ ਦੀ ਤਸਦੀਕ ਕਰੋ', complete: 'ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਪੂਰੀ ਕਰੋ', retry: 'ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ' },
  ur: { title: 'اپنا WAOOAW اکاؤنٹ بنائیں', displayName: 'آپ کا نام', businessName: 'کاروبار کا نام', businessDomain: 'کاروبار کی قسم', email: 'ای میل پتہ', mobile: 'موبائل نمبر', code: 'چھ ہندسوں کا کوڈ', saveProfile: 'محفوظ کریں اور جاری رکھیں', sendCode: 'تصدیقی کوڈ بھیجیں', verifyCode: 'کوڈ کی تصدیق کریں', complete: 'رجسٹریشن مکمل کریں', retry: 'دوبارہ کوشش کریں' },
};

export function getIdentityMessages(locale: SupportedLocale): IdentityMessages {
  return { ...en, ...translations[locale] };
}