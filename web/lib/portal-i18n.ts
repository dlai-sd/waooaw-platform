// Implements: work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md §8.2 Information Architecture
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import type { SupportedLocale } from './preferences';

type PortalMessages = {
  alerts: string;
  marketplace: string;
  myAgents: string;
  verified: string;
};

export const portalMessages: Record<SupportedLocale, PortalMessages> = {
  en: { alerts: 'Alerts', marketplace: 'Marketplace', myAgents: 'My Agents', verified: 'Verified' },
  hi: { alerts: 'सूचनाएँ', marketplace: 'मार्केटप्लेस', myAgents: 'मेरे एजेंट', verified: 'सत्यापित' },
  mr: { alerts: 'सूचना', marketplace: 'मार्केटप्लेस', myAgents: 'माझे एजंट', verified: 'सत्यापित' },
  ta: { alerts: 'அறிவிப்புகள்', marketplace: 'சந்தை', myAgents: 'என் முகவர்கள்', verified: 'சரிபார்க்கப்பட்டது' },
  te: { alerts: 'హెచ్చరికలు', marketplace: 'మార్కెట్‌ప్లేస్', myAgents: 'నా ఏజెంట్లు', verified: 'ధృవీకరించబడింది' },
  kn: { alerts: 'ಎಚ್ಚರಿಕೆಗಳು', marketplace: 'ಮಾರುಕಟ್ಟೆ', myAgents: 'ನನ್ನ ಏಜೆಂಟ್‌ಗಳು', verified: 'ಪರಿಶೀಲಿಸಲಾಗಿದೆ' },
  gu: { alerts: 'ચેતવણીઓ', marketplace: 'માર્કેટપ્લેસ', myAgents: 'મારા એજન્ટો', verified: 'ચકાસાયેલ' },
  bn: { alerts: 'সতর্কতা', marketplace: 'মার্কেটপ্লেস', myAgents: 'আমার এজেন্ট', verified: 'যাচাইকৃত' },
  ml: { alerts: 'അറിയിപ്പുകൾ', marketplace: 'മാർക്കറ്റ്‌പ്ലേസ്', myAgents: 'എന്റെ ഏജന്റുമാർ', verified: 'പരിശോധിച്ചു' },
  pa: { alerts: 'ਸੂਚਨਾਵਾਂ', marketplace: 'ਮਾਰਕੀਟਪਲੇਸ', myAgents: 'ਮੇਰੇ ਏਜੰਟ', verified: 'ਪ੍ਰਮਾਣਿਤ' },
  ur: { alerts: 'اطلاعات', marketplace: 'مارکیٹ پلیس', myAgents: 'میرے ایجنٹس', verified: 'تصدیق شدہ' },
};