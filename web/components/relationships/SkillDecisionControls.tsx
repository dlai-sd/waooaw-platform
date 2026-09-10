'use client';

import { useState } from 'react';
import type { RelationshipEvaluationProjection } from '@/lib/api/relationships';

type Skill = RelationshipEvaluationProjection['skills'][number];
const actions = ['SELECT_SKILL', 'UPDATE_SKILL', 'ACCEPT_SKILL', 'DEFER_SKILL'] as const;

export function SkillDecisionControls({ relationshipId, workspaceVersion, skills }: { relationshipId: string; workspaceVersion: string; skills: Skill[] }) {
  const [message, setMessage] = useState('');
  async function decide(skill: Skill, commandKind: typeof actions[number]) {
    setMessage('Saving skill decision...');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/skill-decisions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idempotencyKey: crypto.randomUUID(), command: { schemaVersion: '1.0', expectedWorkspaceVersion: workspaceVersion, expectedSubjectVersion: skill.subjectVersion, payload: { commandKind, configurationId: skill.configurationId, skillId: skill.skillId, skillVersion: skill.skillVersion } } }) });
    setMessage(response.ok ? 'Skill decision recorded.' : 'Skill decision could not be recorded. Re-authentication or refreshed data may be required.');
  }
  if (!skills.length) return null;
  return <section className="relationship-summary" aria-labelledby="skill-decisions-title"><div><p className="section-label">Skills</p><h2 id="skill-decisions-title">Choose skills for this expert</h2></div><ul className="decision-list">{skills.map((skill) => <li key={skill.configurationId}><span><strong>{skill.skillId.replaceAll('_', ' ').toLowerCase()}</strong><small>{skill.skillVersion} · {skill.status.toLowerCase()}</small></span><div>{actions.map((action) => <button className="secondary-link" key={action} onClick={() => void decide(skill, action)} type="button">{action.replace('_SKILL', '').toLowerCase()}</button>)}</div></li>)}</ul><p role="status">{message}</p></section>;
}