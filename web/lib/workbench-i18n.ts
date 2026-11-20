// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability), C-063

import type { SupportedLocale } from './preferences';

export type WorkbenchMessages = {
  title: string;
  toolsLabel: string;
  talk: string;
  refresh: string;
  refreshing: string;
  refreshFailed: string;
  toolOverview: string;
  toolGoals: string;
  toolPlan: string;
  toolCapabilities: string;
  toolDecisions: string;
  toolMonitor: string;
  toolWallet: string;
  toolEvidence: string;
  nextStep: string;
  nothingNeeded: string;
  readiness: string;
  readinessInduction: string;
  readinessPlan: string;
  readinessOperations: string;
  readinessPerformance: string;
  limitations: string;
  alerts: string;
  noAlerts: string;
  evidenceState: string;
  freshness: string;
  goals: string;
  noGoals: string;
  startGoal: string;
  goalName: string;
  saveGoal: string;
  reviseGoal: string;
  reasonForChange: string;
  goalVersion: string;
  plan: string;
  noPlan: string;
  proposePlan: string;
  agreePlan: string;
  acknowledgeLimits: string;
  milestones: string;
  calendar: string;
  capabilities: string;
  noCapabilities: string;
  enable: string;
  pause: string;
  resume: string;
  runNow: string;
  approvalMode: string;
  allowanceUsed: string;
  nextRun: string;
  decisions: string;
  noDecisions: string;
  approve: string;
  decline: string;
  defer: string;
  decidedBy: string;
  cost: string;
  expires: string;
  monitor: string;
  noTiles: string;
  target: string;
  trend: string;
  workItems: string;
  noWorkItems: string;
  owner: string;
  wallet: string;
  noComponents: string;
  remaining: string;
  periodEnds: string;
  topUp: string;
  topUpQuantity: string;
  topUpComponent: string;
  price: string;
  topUpStates: Record<string, string>;
  askAccountOwner: string;
  evidence: string;
  noEvidence: string;
  exportEvidence: string;
  exportRequested: string;
  controls: string;
  stop: string;
  stopConfirm: string;
  pauseWork: string;
  cancel: string;
  working: string;
  done: string;
  signInAgain: string;
  strongAuth: string;
  openLink: string;
  handoffInvalid: string;
  unsupportedBlock: string;
  states: Record<string, string>;
  freshnessStates: Record<string, string>;
  evidenceStates: Record<string, string>;
  planStates: Record<string, string>;
  capabilityStates: Record<string, string>;
  phases: Record<string, string>;
  problems: Record<string, string>;
};

const en: WorkbenchMessages = {
  title: 'Workbench',
  toolsLabel: 'Workbench tools',
  talk: 'Talk to your professional',
  refresh: 'Refresh',
  refreshing: 'Refreshing',
  refreshFailed: 'The workbench could not be refreshed.',
  toolOverview: 'Overview',
  toolGoals: 'Goals',
  toolPlan: 'Plan',
  toolCapabilities: 'Capabilities',
  toolDecisions: 'Decisions',
  toolMonitor: 'Monitor',
  toolWallet: 'Allowance',
  toolEvidence: 'Evidence',
  nextStep: 'Recommended next step',
  nothingNeeded: 'Nothing needs your attention.',
  readiness: 'Readiness',
  readinessInduction: 'Induction',
  readinessPlan: 'Plan',
  readinessOperations: 'Operations',
  readinessPerformance: 'Performance',
  limitations: 'Limits on this view',
  alerts: 'Alerts',
  noAlerts: 'No alerts.',
  evidenceState: 'Evidence',
  freshness: 'Data freshness',
  goals: 'Goals',
  noGoals: 'No goals are set yet.',
  startGoal: 'Set your first goal',
  goalName: 'Goal name',
  saveGoal: 'Save goal',
  reviseGoal: 'Revise goal',
  reasonForChange: 'Reason for the change',
  goalVersion: 'Version',
  plan: 'Plan',
  noPlan: 'There is no plan yet.',
  proposePlan: 'Propose a plan',
  agreePlan: 'Agree the plan',
  acknowledgeLimits: 'I understand the limits listed on this plan',
  milestones: 'Milestones',
  calendar: 'Calendar',
  capabilities: 'Capabilities',
  noCapabilities: 'No capabilities are declared yet.',
  enable: 'Enable',
  pause: 'Pause',
  resume: 'Resume',
  runNow: 'Run now',
  approvalMode: 'Approval mode',
  allowanceUsed: 'Uses allowance',
  nextRun: 'Next run',
  decisions: 'Decisions',
  noDecisions: 'Nothing is waiting for your decision.',
  approve: 'Approve',
  decline: 'Not now',
  defer: 'Ask me later',
  decidedBy: 'Decided by',
  cost: 'Cost',
  expires: 'Expires',
  monitor: 'Monitor',
  noTiles: 'No measures are reported yet.',
  target: 'Target',
  trend: 'Trend',
  workItems: 'Work items',
  noWorkItems: 'No work items yet.',
  owner: 'Owner',
  wallet: 'Allowance',
  noComponents: 'No allowance is available yet.',
  remaining: 'Remaining',
  periodEnds: 'Period ends',
  topUp: 'Add to your allowance',
  topUpQuantity: 'Quantity',
  topUpComponent: 'Item to add',
  price: 'Price, GST included',
  topUpStates: {
    PENDING_PAYMENT: 'Waiting for payment before it is added.',
    CREDITED: 'Added to your allowance.',
    FAILED: 'It could not be added. Nothing was charged.',
  },
  askAccountOwner: 'Ask the account owner to add more.',
  evidence: 'Evidence',
  noEvidence: 'No evidence has been recorded yet.',
  exportEvidence: 'Export evidence',
  exportRequested: 'Export requested',
  controls: 'Controls',
  stop: 'Stop',
  stopConfirm: 'Stop all work now',
  pauseWork: 'Pause',
  cancel: 'Cancel',
  working: 'Working',
  done: 'Done',
  signInAgain: 'Sign in again',
  strongAuth: 'A fresh strong sign-in is required for this action.',
  openLink: 'Open',
  handoffInvalid: 'This link is not valid any more. Ask your professional for a new one.',
  unsupportedBlock: 'This item cannot be shown here.',
  states: {
    PROPOSED: 'Proposed',
    READY: 'Ready',
    IN_PROGRESS: 'In progress',
    WAITING_ON_CUSTOMER: 'Waiting for you',
    WAITING_ON_AGENT: 'Waiting for your professional',
    WAITING_ON_PLATFORM: 'Waiting for the platform',
    BLOCKED: 'Blocked',
    COMPLETED: 'Completed',
    DEFERRED: 'Deferred',
    CANCELLED: 'Cancelled',
    SUPERSEDED: 'Superseded',
    OUTCOME_UNKNOWN: 'Outcome not known',
    UNAVAILABLE: 'Not available',
    ACTIVE: 'Active',
    PAUSED: 'Paused',
  },
  freshnessStates: {
    CURRENT: 'Up to date',
    STALE: 'Out of date',
    UNKNOWN: 'Not known',
    UNAVAILABLE: 'Not available',
  },
  evidenceStates: {
    PENDING: 'Pending',
    RECORDED: 'Recorded',
    UNAVAILABLE: 'Not available',
    DISPUTED: 'Disputed',
    SUPERSEDED: 'Superseded',
  },
  planStates: {
    DRAFT: 'Draft',
    READY_FOR_REVIEW: 'Ready for your review',
    AGREED: 'Agreed',
    SUPERSEDED: 'Superseded',
  },
  capabilityStates: {
    ACTIVE: 'Active',
    PAUSED: 'Paused',
    NOT_ENABLED: 'Not enabled',
    AVAILABLE: 'Available',
    DEFAULT_OFF: 'Off until you enable it',
    UNAVAILABLE: 'Not available',
  },
  phases: {
    INDUCTION: 'Induction',
    PLANNING: 'Planning',
    OPERATIONS: 'Operations',
  },
  problems: {
    WORKBENCH_DISABLED: 'The workbench is not available yet.',
    WORKBENCH_REQUEST_INVALID: 'This request could not be accepted. Check what you entered and try again.',
    WORKBENCH_VERSION_CONFLICT: 'This changed since you opened it. Refresh and try again.',
    WORKBENCH_IDEMPOTENCY_CONFLICT: 'This request was already used for a different action. Refresh and try again.',
    WORKBENCH_UNAVAILABLE: 'This is not available right now. Nothing was changed.',
    SPEND_PURPOSE_UNMAPPED: 'This work is not covered by an allowance yet. Nothing was changed.',
    SPEND_AUTHORITY_UNAVAILABLE: 'You are not able to spend from this allowance.',
    SPEND_COMMERCIAL_UNAVAILABLE: 'Allowance information is not available right now. Nothing was changed.',
    WALLET_INSUFFICIENT: 'There is not enough allowance left for this.',
    WALLET_IDEMPOTENCY_CONFLICT: 'This request was already used for a different action. Refresh and try again.',
    COMPONENT_NOT_YET_RELEASED: 'This allowance is not released yet.',
    PROACTIVE_ALLOWANCE_EXHAUSTED: 'The allowance for proactive work is used up.',
    TRIAL_ALREADY_USED: 'The trial was already used.',
    TRIAL_ALREADY_USED_BY_IDENTITY: 'The trial was already used.',
    PACKAGE_COMPONENT_NOT_AVAILABLE: 'This package does not include that allowance.',
    SERVICE_UNAVAILABLE: 'This is not available right now. Nothing was changed.',
    REQUEST_INVALID: 'This request could not be accepted.',
  },
};

const hi: WorkbenchMessages = {
  title: 'वर्कबेंच',
  toolsLabel: 'वर्कबेंच टूल',
  talk: 'अपने प्रोफेशनल से बात करें',
  refresh: 'ताज़ा करें',
  refreshing: 'ताज़ा हो रहा है',
  refreshFailed: 'वर्कबेंच ताज़ा नहीं हो सका।',
  toolOverview: 'सारांश',
  toolGoals: 'लक्ष्य',
  toolPlan: 'योजना',
  toolCapabilities: 'क्षमताएँ',
  toolDecisions: 'निर्णय',
  toolMonitor: 'निगरानी',
  toolWallet: 'सीमा',
  toolEvidence: 'प्रमाण',
  nextStep: 'सुझाया गया अगला कदम',
  nothingNeeded: 'आपके ध्यान की कोई ज़रूरत नहीं है।',
  readiness: 'तैयारी',
  readinessInduction: 'परिचय',
  readinessPlan: 'योजना',
  readinessOperations: 'संचालन',
  readinessPerformance: 'प्रदर्शन',
  limitations: 'इस दृश्य की सीमाएँ',
  alerts: 'सूचनाएँ',
  noAlerts: 'कोई सूचना नहीं है।',
  evidenceState: 'प्रमाण',
  freshness: 'जानकारी कितनी नई है',
  goals: 'लक्ष्य',
  noGoals: 'अभी कोई लक्ष्य तय नहीं है।',
  startGoal: 'अपना पहला लक्ष्य तय करें',
  goalName: 'लक्ष्य का नाम',
  saveGoal: 'लक्ष्य सहेजें',
  reviseGoal: 'लक्ष्य बदलें',
  reasonForChange: 'बदलाव का कारण',
  goalVersion: 'संस्करण',
  plan: 'योजना',
  noPlan: 'अभी कोई योजना नहीं है।',
  proposePlan: 'योजना का प्रस्ताव दें',
  agreePlan: 'योजना स्वीकार करें',
  acknowledgeLimits: 'मैं इस योजना की सूचीबद्ध सीमाएँ समझता/समझती हूँ',
  milestones: 'पड़ाव',
  calendar: 'कैलेंडर',
  capabilities: 'क्षमताएँ',
  noCapabilities: 'अभी कोई क्षमता घोषित नहीं है।',
  enable: 'चालू करें',
  pause: 'विराम दें',
  resume: 'फिर शुरू करें',
  runNow: 'अभी चलाएँ',
  approvalMode: 'स्वीकृति का तरीका',
  allowanceUsed: 'सीमा से खर्च होता है',
  nextRun: 'अगली बार',
  decisions: 'निर्णय',
  noDecisions: 'आपके निर्णय के लिए कुछ भी लंबित नहीं है।',
  approve: 'स्वीकृत करें',
  decline: 'अभी नहीं',
  defer: 'बाद में पूछें',
  decidedBy: 'निर्णय लेने वाला',
  cost: 'लागत',
  expires: 'समाप्ति',
  monitor: 'निगरानी',
  noTiles: 'अभी कोई माप दर्ज नहीं है।',
  target: 'लक्ष्य मान',
  trend: 'रुझान',
  workItems: 'काम की सूची',
  noWorkItems: 'अभी कोई काम नहीं है।',
  owner: 'ज़िम्मेदार',
  wallet: 'सीमा',
  noComponents: 'अभी कोई सीमा उपलब्ध नहीं है।',
  remaining: 'शेष',
  periodEnds: 'अवधि समाप्त',
  topUp: 'अपनी सीमा बढ़ाएँ',
  topUpQuantity: 'मात्रा',
  topUpComponent: 'जोड़ने की वस्तु',
  price: 'कीमत, जीएसटी सहित',
  topUpStates: {
    PENDING_PAYMENT: 'जोड़ने से पहले भुगतान की प्रतीक्षा है।',
    CREDITED: 'आपकी सीमा में जोड़ दिया गया।',
    FAILED: 'जोड़ा नहीं जा सका। कुछ भी नहीं काटा गया।',
  },
  askAccountOwner: 'और जोड़ने के लिए खाता स्वामी से कहें।',
  evidence: 'प्रमाण',
  noEvidence: 'अभी कोई प्रमाण दर्ज नहीं है।',
  exportEvidence: 'प्रमाण निर्यात करें',
  exportRequested: 'निर्यात का अनुरोध किया गया',
  controls: 'नियंत्रण',
  stop: 'रोकें',
  stopConfirm: 'अभी सारा काम रोकें',
  pauseWork: 'विराम दें',
  cancel: 'रद्द करें',
  working: 'काम जारी है',
  done: 'पूर्ण',
  signInAgain: 'फिर से साइन इन करें',
  strongAuth: 'इस कार्य के लिए अभी-अभी किया गया मज़बूत साइन-इन ज़रूरी है।',
  openLink: 'खोलें',
  handoffInvalid: 'यह लिंक अब मान्य नहीं है। अपने प्रोफेशनल से नया लिंक माँगें।',
  unsupportedBlock: 'यह आइटम यहाँ नहीं दिखाया जा सकता।',
  states: {
    PROPOSED: 'प्रस्तावित',
    READY: 'तैयार',
    IN_PROGRESS: 'जारी है',
    WAITING_ON_CUSTOMER: 'आपकी प्रतीक्षा है',
    WAITING_ON_AGENT: 'आपके प्रोफेशनल की प्रतीक्षा है',
    WAITING_ON_PLATFORM: 'प्लेटफ़ॉर्म की प्रतीक्षा है',
    BLOCKED: 'रुका हुआ',
    COMPLETED: 'पूरा हुआ',
    DEFERRED: 'टाला गया',
    CANCELLED: 'रद्द',
    SUPERSEDED: 'बदला गया',
    OUTCOME_UNKNOWN: 'नतीजा ज्ञात नहीं',
    UNAVAILABLE: 'उपलब्ध नहीं',
    ACTIVE: 'सक्रिय',
    PAUSED: 'विराम पर',
  },
  freshnessStates: {
    CURRENT: 'ताज़ा',
    STALE: 'पुराना',
    UNKNOWN: 'ज्ञात नहीं',
    UNAVAILABLE: 'उपलब्ध नहीं',
  },
  evidenceStates: {
    PENDING: 'लंबित',
    RECORDED: 'दर्ज',
    UNAVAILABLE: 'उपलब्ध नहीं',
    DISPUTED: 'विवादित',
    SUPERSEDED: 'बदला गया',
  },
  planStates: {
    DRAFT: 'मसौदा',
    READY_FOR_REVIEW: 'आपकी समीक्षा के लिए तैयार',
    AGREED: 'स्वीकृत',
    SUPERSEDED: 'बदली गई',
  },
  capabilityStates: {
    ACTIVE: 'सक्रिय',
    PAUSED: 'विराम पर',
    NOT_ENABLED: 'चालू नहीं',
    AVAILABLE: 'उपलब्ध',
    DEFAULT_OFF: 'आपके चालू करने तक बंद',
    UNAVAILABLE: 'उपलब्ध नहीं',
  },
  phases: {
    INDUCTION: 'परिचय',
    PLANNING: 'योजना',
    OPERATIONS: 'संचालन',
  },
  problems: {
    WORKBENCH_DISABLED: 'वर्कबेंच अभी उपलब्ध नहीं है।',
    WORKBENCH_REQUEST_INVALID: 'यह अनुरोध स्वीकार नहीं हो सका। जो लिखा है उसे जाँचकर फिर कोशिश करें।',
    WORKBENCH_VERSION_CONFLICT: 'आपके खोलने के बाद यह बदल गया है। ताज़ा करके फिर कोशिश करें।',
    WORKBENCH_IDEMPOTENCY_CONFLICT: 'यह अनुरोध पहले किसी दूसरे कार्य के लिए इस्तेमाल हो चुका है। ताज़ा करके फिर कोशिश करें।',
    WORKBENCH_UNAVAILABLE: 'यह अभी उपलब्ध नहीं है। कुछ भी नहीं बदला गया।',
    SPEND_PURPOSE_UNMAPPED: 'यह काम अभी किसी सीमा में शामिल नहीं है। कुछ भी नहीं बदला गया।',
    SPEND_AUTHORITY_UNAVAILABLE: 'आप इस सीमा से खर्च नहीं कर सकते।',
    SPEND_COMMERCIAL_UNAVAILABLE: 'सीमा की जानकारी अभी उपलब्ध नहीं है। कुछ भी नहीं बदला गया।',
    WALLET_INSUFFICIENT: 'इसके लिए सीमा में पर्याप्त शेष नहीं है।',
    WALLET_IDEMPOTENCY_CONFLICT: 'यह अनुरोध पहले किसी दूसरे कार्य के लिए इस्तेमाल हो चुका है। ताज़ा करके फिर कोशिश करें।',
    COMPONENT_NOT_YET_RELEASED: 'यह सीमा अभी जारी नहीं हुई है।',
    PROACTIVE_ALLOWANCE_EXHAUSTED: 'स्वतः भेजे जाने वाले संदेशों की सीमा पूरी हो गई है।',
    TRIAL_ALREADY_USED: 'ट्रायल पहले ही इस्तेमाल हो चुका है।',
    TRIAL_ALREADY_USED_BY_IDENTITY: 'ट्रायल पहले ही इस्तेमाल हो चुका है।',
    PACKAGE_COMPONENT_NOT_AVAILABLE: 'इस पैकेज में वह सीमा शामिल नहीं है।',
    SERVICE_UNAVAILABLE: 'यह अभी उपलब्ध नहीं है। कुछ भी नहीं बदला गया।',
    REQUEST_INVALID: 'यह अनुरोध स्वीकार नहीं हो सका।',
  },
};

export function workbenchMessages(locale: SupportedLocale): WorkbenchMessages {
  return locale === 'hi' ? hi : en;
}

// Declared identifiers never reach the customer raw; an unknown value is shown as plain words.
export function plainWords(identifier: string): string {
  const words = identifier.replace(/[_-]+/g, ' ').trim().toLowerCase();
  return words.length === 0 ? identifier : words.charAt(0).toUpperCase() + words.slice(1);
}

export function labelFor(map: Record<string, string>, key: string): string {
  return map[key] ?? plainWords(key);
}
