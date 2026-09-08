const root = document.documentElement;
const viewPanels = [...document.querySelectorAll('[data-view-panel]')];
const viewCommands = [...document.querySelectorAll('[data-view]')];
const drawer = document.querySelector('#account-drawer');
const drawerScrim = document.querySelector('#drawer-scrim');
const drawerPanel = document.querySelector('#drawer-panel');
const detailDialog = document.querySelector('#detail-dialog');
const toast = document.querySelector('#toast');
const globalNavigation = document.querySelector('#global-navigation');
const agentsOverview = document.querySelector('#agents-overview');
const agentWorkspace = document.querySelector('#agent-workspace');
const contextPanel = document.querySelector('#context-panel');
const myAgentsView = document.querySelector('#my-agents');
const messageInput = document.querySelector('#message-input');
const voiceReview = document.querySelector('#voice-review');
const chatContext = document.querySelector('#chat-context');
let toastTimer;
let voiceTimer;
let voiceSeconds = 0;

const viewMeta = {
  'my-agents': ['Customer Portal', 'Shivneri Farms'],
  marketplace: ['Marketplace', 'Browse published professionals'],
  alerts: ['Alerts', '3 items · 1 decision required'],
};

function showToast(message) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toastTimer = window.setTimeout(() => { toast.hidden = true; }, 3200);
}

function setView(viewName) {
  viewPanels.forEach((panel) => { panel.hidden = panel.dataset.viewPanel !== viewName; });
  viewCommands.forEach((command) => {
    const active = command.dataset.view === viewName;
    command.classList.toggle('is-active', active);
    if (active) command.setAttribute('aria-current', 'page');
    else command.removeAttribute('aria-current');
  });
  const [title, subtitle] = viewMeta[viewName];
  document.querySelector('#header-title').textContent = title;
  document.querySelector('#header-subtitle').textContent = subtitle;
  if (viewName === 'my-agents') {
    agentsOverview.hidden = false;
    agentWorkspace.hidden = true;
  }
}

function openDrawer(viewName) {
  drawer.classList.add('is-open');
  drawer.setAttribute('aria-hidden', 'false');
  drawerScrim.hidden = false;
  document.querySelector('#menu-button').setAttribute('aria-expanded', 'true');
  document.querySelector('#desktop-account-button').setAttribute('aria-expanded', 'true');
  if (viewName) renderDrawerPanel(viewName);
  window.setTimeout(() => drawer.querySelector('button').focus(), 0);
}

function closeDrawer() {
  drawer.classList.remove('is-open');
  drawer.setAttribute('aria-hidden', 'true');
  drawerScrim.hidden = true;
  document.querySelector('#menu-button').setAttribute('aria-expanded', 'false');
  document.querySelector('#desktop-account-button').setAttribute('aria-expanded', 'false');
}

function renderDrawerPanel(viewName) {
  const panels = {
    profile: `<p class="eyebrow">Profile</p><h3>Customer account</h3><dl><div><dt>Name</dt><dd>Suresh Kulkarni</dd></div><div><dt>Organization</dt><dd>Shivneri Farms</dd></div><div><dt>Preferred language</dt><dd>English · Marathi available</dd></div><div><dt>Verified channels</dt><dd>Email · WhatsApp</dd></div></dl>`,
    billing: `<p class="eyebrow">Billing</p><h3>Professional plan</h3><dl><div><dt>Current period</dt><dd>62% allowance used</dd></div><div><dt>Forecast</dt><dd>Within approved plan</dd></div><div><dt>Next renewal</dt><dd>18 September 2026</dd></div><div><dt>Open invoices</dt><dd>None</dd></div></dl><p>Figures are fictional prototype data. Production values must come from Billing Engine through Business Platform.</p>`,
    settings: `<p class="eyebrow">Settings</p><h3>Experience</h3><dl><div><dt>Theme</dt><dd>${root.dataset.theme === 'dark' ? 'Dark' : 'Light'}</dd></div><div><dt>Language</dt><dd>English</dd></div><div><dt>Alert channel</dt><dd>Portal and WhatsApp</dd></div><div><dt>Default start</dt><dd>Most recent agent</dd></div></dl><h3>Preview system states</h3><div class="detail-actions"><button type="button" data-state-demo="loading">Loading</button><button type="button" data-state-demo="empty">Empty</button><button type="button" data-state-demo="offline">Offline</button><button type="button" data-state-demo="error">Error</button></div>`,
  };
  drawerPanel.innerHTML = panels[viewName];
  drawerPanel.hidden = false;
}

function setTheme() {
  const dark = root.dataset.theme !== 'dark';
  root.dataset.theme = dark ? 'dark' : 'light';
  const button = document.querySelector('#theme-button');
  button.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`);
  document.querySelector('#theme-icon').textContent = dark ? '☀' : '☾';
}

function syncContextPanel() {
  const overlay = window.matchMedia('(max-width: 1240px)').matches;
  if (overlay) {
    contextPanel.classList.remove('is-dismissed');
    contextPanel.classList.remove('is-open');
    myAgentsView.classList.remove('context-collapsed');
  }
  document.querySelector('#context-button').setAttribute('aria-expanded', String(!overlay && !contextPanel.classList.contains('is-dismissed')));
}

function selectAgent(agentName) {
  const profiles = {
    asha: { name: 'Asha', status: 'Employed · In operation', theme: 'agriculture', configuration: 'Complete · 2 of 2', induction: ['Shivneri Farms context tuned through conversation', 'Verified'], goal: 'Verified · 3 goals', skills: ['3 skills available for goal setting', '3'], goals: ['Precise targets linked to each skill', '3'], verification: ['Weekly cadence confirmed by customer', 'Verified'], outcomes: '2 outcomes · On track', outcomeItems: [['Crop readiness', 'Linked to seasonal planning · Weekly', 'On track'], ['Input efficiency', 'Linked to resource guidance · Monthly', 'Measuring']], operation: 'Available · Goals verified', opening: 'Good morning, Suresh. Rain is expected late Thursday. I moved the cotton spray recommendation to Wednesday morning.', action: 'Prepare field before Thursday rain', customer: "Will the change affect this week's budget?", response: 'No. It changes timing only. Your approved weekly allowance remains the same.', context: 'Goal Setting / Goals and measures' },
    maya: { name: 'Maya', status: 'Trial · Pending goal setting', theme: 'marketing', configuration: 'Induction underway · 1 of 2', induction: ['Learning your audience, offer and growth priorities', 'In progress'], goal: 'Setting goals · 1 of 3', skills: ['4 skills declared for goal setting', '4'], goals: ['One campaign goal drafted for review', '1 draft'], verification: ['Measures and cadence need confirmation', 'Pending'], outcomes: 'Available after goals', outcomeItems: [['Audience growth', 'Available after goal verification', 'Locked'], ['Campaign efficiency', 'Available after goal verification', 'Locked']], operation: 'Locked · Verify goals first', opening: 'I understand you want to grow direct enquiries for Shivneri Farms. I will ask three short questions so we can set a measurable first goal.', action: 'Confirm the primary customer audience', customer: 'Can we focus first on wholesale buyers near Pune?', response: 'Yes. I will tune the proposed goal, measure and weekly review around qualified wholesale enquiries.', context: 'Goal Setting / Goals and measures' },
    tara: { name: 'Tara', status: 'Trial expired · Not in operation', theme: 'trading', configuration: 'Incomplete · 1 of 2', induction: ['Business induction was not completed', 'Incomplete'], goal: 'Not verified', skills: ['3 skills were declared during trial', '3'], goals: ['No goals were customer-verified', '0'], verification: ['No active frequency or verification', 'Not set'], outcomes: 'No active outcomes', outcomeItems: [['Research discipline', 'No verified goal was linked', 'Inactive'], ['Risk awareness', 'No verified measure was linked', 'Inactive']], operation: 'Relationship ended', opening: 'This trial relationship has ended. Previous conversation remains available for review.', action: 'Review the expired trial relationship', customer: 'Can I still see the research topics we discussed?', response: 'Yes. This workspace is read-only, and no new work or consequential action can be started.', context: 'Goal Setting / Goals and measures' }
  };
  const profile = profiles[agentName] || profiles.asha;
  const { name, status, theme } = profile;
  const tara = agentName === 'tara';
  document.querySelector('#agent-name').textContent = name;
  document.querySelector('#agent-status').textContent = status;
  document.querySelector('#active-avatar').textContent = name.charAt(0);
  document.querySelector('#active-avatar').className = `agent-avatar ${theme}`;
  messageInput.placeholder = `Message ${name}`;
  messageInput.disabled = tara;
  document.querySelector('#voice-button').disabled = tara;
  document.querySelector('.send-button').disabled = tara;
  document.querySelector('.conversation').setAttribute('aria-label', `Conversation with ${name}`);
  document.querySelector('#configuration-summary').textContent = profile.configuration;
  document.querySelector('#induct-detail').textContent = profile.induction[0];
  document.querySelector('#induct-state').textContent = profile.induction[1];
  document.querySelector('#goal-summary').textContent = profile.goal;
  [['skills', profile.skills], ['goals', profile.goals], ['verification', profile.verification]].forEach(([id, content]) => {
    document.querySelector(`#${id}-detail`).textContent = content[0];
    document.querySelector(`#${id}-state`).textContent = content[1];
  });
  document.querySelector('#outcomes-summary').textContent = profile.outcomes;
  profile.outcomeItems.forEach((outcome, index) => {
    const id = index === 0 ? 'one' : 'two';
    document.querySelector(`#outcome-${id}-title`).textContent = outcome[0];
    document.querySelector(`#outcome-${id}-detail`).textContent = outcome[1];
    document.querySelector(`#outcome-${id}-state`).textContent = outcome[2];
  });
  document.querySelector('#operation-summary').textContent = profile.operation;
  document.querySelector('#agent-opening-message').textContent = profile.opening;
  document.querySelector('#agent-action-title').textContent = profile.action;
  document.querySelector('.work-card').setAttribute('aria-label', `Action required: ${profile.action}`);
  document.querySelector('#customer-message').textContent = profile.customer;
  document.querySelector('#agent-response-message').textContent = profile.response;
  chatContext.textContent = `Discussing: ${profile.context}`;
  const operationGroup = document.querySelector('#operation-group');
  const goalsVerified = agentName === 'asha';
  operationGroup.classList.toggle('is-locked', !goalsVerified);
  operationGroup.querySelectorAll('.accordion-items button').forEach((button) => { button.disabled = !goalsVerified; });
  const outcomesGroup = document.querySelector('#outcomes-group');
  outcomesGroup.classList.toggle('is-locked', !goalsVerified);
  outcomesGroup.querySelectorAll('.accordion-items button').forEach((button) => { button.disabled = !goalsVerified; });
  agentsOverview.hidden = true;
  agentWorkspace.hidden = false;
  document.querySelector('#header-title').textContent = name;
  document.querySelector('#header-subtitle').textContent = status;
  if (tara) showToast('This trial has expired. The workspace is read-only.');
  syncContextPanel();
}

function formatVoiceTime() {
  return `0:${String(voiceSeconds).padStart(2, '0')}`;
}

function stopVoice(cancelled = false) {
  window.clearInterval(voiceTimer);
  voiceTimer = undefined;
  voiceReview.hidden = true;
  voiceSeconds = 0;
  document.querySelector('#voice-timer').textContent = '0:00';
  document.querySelector('#voice-button').setAttribute('aria-label', 'Record voice note');
  if (cancelled) showToast('Voice draft discarded. No audio was recorded or uploaded.');
}

viewCommands.forEach((command) => command.addEventListener('click', () => setView(command.dataset.view)));
document.querySelector('#rail-toggle').addEventListener('click', () => {
  const collapsed = globalNavigation.classList.toggle('is-collapsed');
  document.querySelector('#rail-toggle').setAttribute('aria-expanded', String(!collapsed));
  document.querySelector('#rail-toggle').setAttribute('aria-label', collapsed ? 'Expand navigation' : 'Collapse navigation');
});
document.querySelector('#menu-button').addEventListener('click', () => openDrawer());
document.querySelector('#desktop-account-button').addEventListener('click', () => openDrawer());
document.querySelector('#close-drawer').addEventListener('click', closeDrawer);
drawerScrim.addEventListener('click', closeDrawer);
document.querySelector('#theme-button').addEventListener('click', setTheme);
document.querySelectorAll('[data-drawer-view]').forEach((button) => button.addEventListener('click', () => openDrawer(button.dataset.drawerView)));
document.querySelectorAll('[data-open-agent]').forEach((button) => button.addEventListener('click', () => selectAgent(button.dataset.openAgent)));
document.querySelector('#agent-list-button').addEventListener('click', () => {
  agentWorkspace.hidden = true;
  agentsOverview.hidden = false;
  document.querySelector('#header-title').textContent = 'Customer Portal';
  document.querySelector('#header-subtitle').textContent = 'Shivneri Farms';
});
document.querySelector('#context-button').addEventListener('click', () => {
  contextPanel.classList.remove('is-dismissed');
  myAgentsView.classList.remove('context-collapsed');
  contextPanel.classList.add('is-open');
  document.querySelector('#context-button').setAttribute('aria-expanded', 'true');
});
document.querySelector('#close-context').addEventListener('click', () => {
  contextPanel.classList.remove('is-open');
  if (!window.matchMedia('(max-width: 1240px)').matches) {
    contextPanel.classList.add('is-dismissed');
    myAgentsView.classList.add('context-collapsed');
  }
  document.querySelector('#context-button').setAttribute('aria-expanded', 'false');
});
document.querySelectorAll('.accordion-trigger').forEach((trigger) => trigger.addEventListener('click', () => {
  const group = trigger.closest('.accordion-group');
  const opening = !group.classList.contains('is-open');
  document.querySelectorAll('.accordion-group').forEach((item) => {
    item.classList.remove('is-open');
    item.querySelector('.accordion-trigger').setAttribute('aria-expanded', 'false');
    item.querySelector('.accordion-trigger > span:last-child').textContent = '⌄';
    item.querySelector('.accordion-items').hidden = true;
  });
  if (opening) {
    group.classList.add('is-open');
    trigger.setAttribute('aria-expanded', 'true');
    trigger.querySelector('span:last-child').textContent = '⌃';
    group.querySelector('.accordion-items').hidden = false;
  }
}));
document.querySelectorAll('[data-chat-context]').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('[data-chat-context]').forEach((item) => item.classList.toggle('is-selected', item === button));
  chatContext.textContent = `Discussing: ${button.dataset.chatContext}`;
}));
document.querySelectorAll('[data-context-target]').forEach((button) => button.addEventListener('click', () => {
  const target = document.querySelector(`[data-context-id="${button.dataset.contextTarget}"]`);
  target?.click();
  contextPanel.classList.add('is-open');
}));

document.querySelector('#composer').addEventListener('submit', (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  const message = document.createElement('div');
  message.className = 'message message-customer';
  const body = document.createElement('p');
  body.textContent = text;
  const status = document.createElement('span');
  status.textContent = 'Now · Accepted (prototype)';
  message.append(body, status);
  document.querySelector('#message-stream').append(message);
  messageInput.value = '';
  message.scrollIntoView({ behavior: root.matches('[data-reduced-motion="true"]') ? 'auto' : 'smooth' });
});

document.querySelector('#voice-button').addEventListener('click', () => {
  if (voiceTimer) {
    document.querySelector('#voice-title').textContent = 'Voice draft ready to review';
    window.clearInterval(voiceTimer);
    voiceTimer = undefined;
    showToast('Voice draft ready. Production would require review and explicit send.');
    return;
  }
  voiceReview.hidden = false;
  document.querySelector('#voice-title').textContent = 'Recording voice note';
  document.querySelector('#voice-button').setAttribute('aria-label', 'Stop voice recording');
  voiceTimer = window.setInterval(() => {
    voiceSeconds += 1;
    document.querySelector('#voice-timer').textContent = formatVoiceTime();
    if (voiceSeconds >= 30) {
      window.clearInterval(voiceTimer);
      voiceTimer = undefined;
      document.querySelector('#voice-title').textContent = 'Voice draft ready to review';
    }
  }, 1000);
});
document.querySelector('#cancel-voice').addEventListener('click', () => stopVoice(true));

const filterButtons = [...document.querySelectorAll('[data-filter]')];
function filterMarket() {
  const activeFilter = document.querySelector('[data-filter].is-active').dataset.filter;
  const query = document.querySelector('#market-search').value.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll('.market-card').forEach((card) => {
    const matchesFilter = activeFilter === 'all' || card.dataset.category === activeFilter;
    const matchesSearch = !query || card.dataset.search.includes(query) || card.textContent.toLowerCase().includes(query);
    card.hidden = !(matchesFilter && matchesSearch);
    if (!card.hidden) visible += 1;
  });
  document.querySelector('#market-empty').hidden = visible !== 0;
}
filterButtons.forEach((button) => button.addEventListener('click', () => {
  filterButtons.forEach((item) => item.classList.toggle('is-active', item === button));
  filterMarket();
}));
document.querySelector('#market-search').addEventListener('input', filterMarket);

document.querySelectorAll('[data-trial]').forEach((button) => button.addEventListener('click', () => {
  const name = button.dataset.trial;
  document.querySelector('#detail-title').textContent = name;
  document.querySelector('#detail-content').innerHTML = `<p>This preview would show the published scope, explicit limits, pricing source, and trial terms supplied by Business Platform.</p><ul><li>No agent is hired from this prototype.</li><li>Trial eligibility must be confirmed by the server.</li><li>Consequential terms require explicit customer acceptance.</li></ul><div class="detail-actions"><button type="button" data-close-dialog>Back</button><button class="primary-action" type="button" data-demo="Trial request is disabled in the prototype">Review trial terms</button></div>`;
  detailDialog.showModal();
}));

document.addEventListener('click', (event) => {
  const closeButton = event.target.closest('[data-close-dialog]');
  if (closeButton) detailDialog.close();
  const demoButton = event.target.closest('[data-demo]');
  if (demoButton) showToast(demoButton.dataset.demo);
  const readButton = event.target.closest('[data-read]');
  if (readButton) {
    readButton.closest('.alert-item').classList.add('is-read');
    readButton.textContent = 'Read';
    readButton.disabled = true;
  }
  const stateButton = event.target.closest('[data-state-demo]');
  if (stateButton) {
    const states = {
      loading: ['Preparing My Agents', 'The application frame stays stable while current relationships load.'],
      empty: ['No agents yet', 'Browse Marketplace to review a professional before starting a trial.'],
      offline: ['You are offline', 'Your unsent draft stays on this device and is not marked sent.'],
      error: ['This view is temporarily unavailable', 'Nothing was changed. Retry when the service is available. Reference: PROTOTYPE-084.'],
    };
    const [title, description] = states[stateButton.dataset.stateDemo];
    document.querySelector('#detail-title').textContent = title;
    document.querySelector('#detail-content').innerHTML = `<p>${description}</p><div class="detail-actions"><button type="button" data-close-dialog>Close</button></div>`;
    detailDialog.showModal();
  }
});

document.querySelector('#mark-all-read').addEventListener('click', () => {
  document.querySelectorAll('[data-alert-kind="update"]').forEach((alert) => alert.classList.add('is-read'));
  showToast('Informational updates marked read. The decision item is unchanged.');
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && drawer.classList.contains('is-open')) closeDrawer();
});

window.addEventListener('resize', syncContextPanel);
syncContextPanel();