/** @jest-environment node */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? sourceFiles(path) : /\.(ts|tsx)$/.test(name) ? [path] : [];
  });
}

describe('F3/F4/F5/F6 generated client and browser boundary contract', () => {
  it('dependency-closes approved public APIs with the pinned generator', () => {
    const script = readFileSync(join(root, 'scripts/generate-api.sh'), 'utf8');
    const generated = readFileSync(join(root, 'lib/api/generated/apis/ConversationApi.ts'), 'utf8');
    const identity = readFileSync(join(root, 'lib/api/generated/apis/IdentityApi.ts'), 'utf8');
    const employment = readFileSync(join(root, 'lib/api/generated/apis/EmploymentApi.ts'), 'utf8');
    const workspace = readFileSync(join(root, 'lib/api/generated/apis/RelationshipWorkspaceApi.ts'), 'utf8');
    const voice = readFileSync(join(root, 'lib/api/generated/apis/VoiceContributionsApi.ts'), 'utf8');
    const professionals = readFileSync(join(root, 'lib/api/generated/apis/ProfessionalsApi.ts'), 'utf8');
    const version = readFileSync(join(root, 'lib/api/generated/.openapi-generator/VERSION'), 'utf8').trim();
    const generatedApis = readdirSync(join(root, 'lib/api/generated/apis')).sort();

    expect(script).toContain('openapitools/openapi-generator-cli:v7.17.0');
    expect(script).toContain('--generator-name typescript-fetch');
    expect(script).toContain('scripts/openapi_slice.py');
    expect(script).toContain('--tag Identity');
    expect(script).toContain('--tag Conversation');
    expect(script).toContain('--tag Employment');
    expect(script).toContain('--tag Professionals');
    expect(script).toContain('--tag "Relationship Workspace"');
    expect(script).toContain('--tag "Voice Contributions"');
    expect(script).toContain('--schema EmploymentRelationship');
    expect(script).toContain('--schema RelationshipTimelineEntry');
    expect(script).toContain('--input-spec "$CONTAINER_SLICE_PATH"');
    expect(script).toContain('hideGenerationTimestamp=true');
    expect(script).toContain('pnpm exec prettier --write lib/api/generated');
    expect(script).not.toContain('--skip-validate-spec');
    expect(generatedApis).toEqual(['ConversationApi.ts', 'EmploymentApi.ts', 'IdentityApi.ts', 'ProfessionalsApi.ts', 'RelationshipWorkspaceApi.ts', 'VoiceContributionsApi.ts', 'index.ts']);
    expect(version).toBe('7.17.0');
    for (const operation of [
      'listConversationMessages',
      'sendConversationMessage',
      'retryConversationMessage',
      'updateConversationReadPosition',
      'streamConversation',
      'cancelConversationExecution',
    ]) expect(generated).toContain(`async ${operation}(`);
    expect(generated.match(/token\("BearerAuth", \[\]\)/g)).toHaveLength(6);
    expect(identity).toContain('token("BearerAuth", [])');
    expect(identity).toContain('token("PreAccountBearerAuth", [])');
    expect(generated).toContain('The version of the OpenAPI document: 1.8.0');
    for (const operation of [
      'prepareRelationshipHandoff',
      'activateRelationshipHandoff',
      'stopEmploymentRelationship',
      'releaseEmploymentRelationshipStop',
    ]) expect(employment).toContain(`async ${operation}(`);
    expect(employment.match(/token\("BearerAuth", \[\]\)/g)?.length).toBeGreaterThanOrEqual(4);
    for (const operation of [
      'getRelationshipWorkspace', 'getRelationshipWorkspaceChanges', 'getRelationshipPlan',
      'getRelationshipAttention', 'getRelationshipWork', 'getRelationshipResults',
      'getRelationshipUsageBudget', 'getRelationshipRightsControls', 'submitRelationshipCommand',
      'getRelationshipCommand', 'listRelationshipEvidence', 'getRelationshipEvidence',
      'requestRelationshipEvidenceExport', 'getRelationshipEvidenceExport',
    ]) expect(workspace).toContain(`async ${operation}(`);
    expect(workspace).toContain('The version of the OpenAPI document: 1.8.0');
    for (const operation of [
      'createVoiceContributionSession', 'getVoiceContributionSession',
      'uploadVoiceContributionAudio', 'getVoiceContributionTranscript',
      'submitVoiceContributionCorrection', 'sendVoiceContribution',
      'cancelVoiceContributionSession', 'requestVoicePayloadErasure',
    ]) expect(voice).toContain(`async ${operation}(`);
    for (const operation of [
      'getOfferableProfessionalVersions', 'createAgentAdmissionDraft',
      'putAgentAdmissionRevision', 'validateAgentAdmission', 'getAgentAdmissionFindings',
      'submitAgentAdmission', 'approveAgentAdmission', 'rejectAgentAdmission',
      'activateAgentAdmission', 'suspendAgentAdmission', 'supersedeAgentAdmission',
      'retireAgentAdmission',
    ]) expect(professionals).toContain(`async ${operation}(`);
    expect(professionals.match(/token\("BearerAuth", \[\]\)/g)).toHaveLength(11);

    for (const model of [
      'ConversationMessageV1',
      'ConversationStreamEventV1',
      'ConversationCardPayloadV1',
      'GovernedConversationCardV1',
      'ActionCardV1',
      'PlanCardV1',
      'DeliverableCardV1',
      'DecisionCardV1',
      'EmploymentRelationship',
      'RelationshipTimelineEntry',
      'PrepareRelationshipHandoffRequest',
      'ActivateRelationshipHandoffRequest',
      'RelationshipHandoff',
      'NeutralContinuityEnvelope',
      'ReleaseEmploymentRelationshipStopRequest',
      'AgentAdmission',
      'AgentAdmissionValidation',
      'AgentAdmissionFinding',
      'OfferableProfessionalVersion',
    ]) expect(statSync(join(root, `lib/api/generated/models/${model}.ts`)).isFile()).toBe(true);
  });

  it('does not generate prohibited browser, PR, provider, or unrelated API surfaces', () => {
    const generated = sourceFiles(join(root, 'lib/api/generated'))
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');

    expect(generated).not.toMatch(/ProfessionalRuntimeApi|ProviderApi|localhost:5003|localhost:5004/);
    expect(generated).not.toMatch(/\/api\/v1\/(professional-runtime|providers|health|billing|approvals)/);
  });

  it('keeps browser source free of prohibited AI SDK and private runtime/provider locations', () => {
    const browserFiles = [
      ...sourceFiles(join(root, 'components')),
      ...sourceFiles(join(root, 'app')).filter((path) => !path.includes(`${join('app', 'api')}`)),
    ];
    const source = browserFiles.map((path) => readFileSync(path, 'utf8')).join('\n');

    expect(source).not.toMatch(/@ai-sdk\/react/);
    expect(source).not.toMatch(/PROFESSIONAL_RUNTIME_URL|MODEL_PROVIDER|localhost:5003|localhost:5004/);
    expect(source).not.toMatch(/https?:\/\/[^'"`]*\/conversation/);
  });

  it('defines exact compact constraints that cannot create horizontal overflow at 360px', () => {
    const css = readFileSync(join(root, 'app/globals.css'), 'utf8');

    expect(css).toContain('@media (max-width: 599px)');
    expect(css).toMatch(/\.workspace-shell \{ width: 100%; min-width: 0;/);
    expect(css).toMatch(/\.conversation-timeline, \.conversation-composer \{ width: 100%; min-width: 0;/);
    expect(css).toMatch(/\.conversation-message \{ width: 100%; \}/);
    expect(css).toMatch(/\.send-command, \.cancel-command \{ width: 100%; \}/);
  });
});