import type { SupportedLocale } from './preferences';

interface GlobalErrorMessages {
  globalErrorTitle: string;
  globalErrorDescription: string;
  tryAgain: string;
}

export const globalErrorMessages: Record<SupportedLocale, GlobalErrorMessages> = {
  en: { globalErrorTitle: 'Something went wrong', globalErrorDescription: 'The outcome is unknown. Try the request again.', tryAgain: 'Try again' },
  hi: { globalErrorTitle: 'कुछ गलत हो गया', globalErrorDescription: 'परिणाम अज्ञात है। अनुरोध फिर आज़माएँ।', tryAgain: 'फिर आज़माएँ' },
  mr: { globalErrorTitle: 'काहीतरी चूक झाली', globalErrorDescription: 'परिणाम अज्ञात आहे. विनंती पुन्हा करून पहा.', tryAgain: 'पुन्हा प्रयत्न करा' },
  ta: { globalErrorTitle: 'ஏதோ தவறு ஏற்பட்டது', globalErrorDescription: 'முடிவு தெரியவில்லை. கோரிக்கையை மீண்டும் முயல்க.', tryAgain: 'மீண்டும் முயல்க' },
  te: { globalErrorTitle: 'ఏదో తప్పు జరిగింది', globalErrorDescription: 'ఫలితం తెలియదు. అభ్యర్థనను మళ్లీ ప్రయత్నించండి.', tryAgain: 'మళ్లీ ప్రయత్నించండి' },
  kn: { globalErrorTitle: 'ಏನೋ ತಪ್ಪಾಗಿದೆ', globalErrorDescription: 'ಫಲಿತಾಂಶ ತಿಳಿದಿಲ್ಲ. ವಿನಂತಿಯನ್ನು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', tryAgain: 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ' },
  gu: { globalErrorTitle: 'કંઈક ખોટું થયું', globalErrorDescription: 'પરિણામ અજ્ઞાત છે. વિનંતી ફરી અજમાવો.', tryAgain: 'ફરી અજમાવો' },
  bn: { globalErrorTitle: 'কিছু ভুল হয়েছে', globalErrorDescription: 'ফলাফল অজানা। অনুরোধটি আবার চেষ্টা করুন।', tryAgain: 'আবার চেষ্টা করুন' },
  ml: { globalErrorTitle: 'എന്തോ പിഴവ് സംഭവിച്ചു', globalErrorDescription: 'ഫലം അജ്ഞാതമാണ്. അഭ്യർത്ഥന വീണ്ടും ശ്രമിക്കുക.', tryAgain: 'വീണ്ടും ശ്രമിക്കുക' },
  pa: { globalErrorTitle: 'ਕੁਝ ਗਲਤ ਹੋ ਗਿਆ', globalErrorDescription: 'ਨਤੀਜਾ ਅਣਜਾਣ ਹੈ। ਬੇਨਤੀ ਦੁਬਾਰਾ ਅਜ਼ਮਾਓ।', tryAgain: 'ਦੁਬਾਰਾ ਅਜ਼ਮਾਓ' },
  ur: { globalErrorTitle: 'کچھ غلط ہو گیا', globalErrorDescription: 'نتیجہ نامعلوم ہے۔ درخواست دوبارہ آزمائیں۔', tryAgain: 'دوبارہ آزمائیں' },
};
