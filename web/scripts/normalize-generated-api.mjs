import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const generatedRoot = resolve(import.meta.dirname, '../lib/api/generated/models');
const targets = [
  ['RelationshipTypedCommandPayloadV1.ts', [
    'instanceOfAcceptSkillPayloadV1', 'AcceptSkillPayloadV1FromJSON',
    'instanceOfDeferSkillPayloadV1', 'DeferSkillPayloadV1FromJSON',
    'instanceOfSelectSkillPayloadV1', 'SelectSkillPayloadV1FromJSON',
    'instanceOfUpdateSkillPayloadV1', 'UpdateSkillPayloadV1FromJSON',
    'instanceOfVerifyGoalPayloadV1', 'VerifyGoalPayloadV1FromJSON',
  ]],
  ['AcceptSkillPayloadV1.ts', ['mapValues']],
  ['DeferSkillPayloadV1.ts', ['mapValues']],
  ['SelectSkillPayloadV1.ts', ['mapValues']],
  ['UpdateSkillPayloadV1.ts', ['mapValues']],
  ['VerifyGoalPayloadV1.ts', ['mapValues']],
];

for (const [fileName, symbols] of targets) {
  const path = resolve(generatedRoot, fileName);
  let source = readFileSync(path, 'utf8');

  for (const symbol of symbols) {
    const occurrences = source.match(new RegExp(`\\b${symbol}\\b`, 'g'))?.length ?? 0;
    if (occurrences === 0) continue;
    if (occurrences !== 1) throw new Error(
      `${fileName}: expected ${symbol} to be absent or occur once as an unused import; found ${occurrences}`,
    );

    source = source.replace(new RegExp(`^\\s*${symbol},?\\n`, 'm'), '');
    source = source.replace(new RegExp(`^import \\{ ${symbol} \\} from [^;]+;\\n`, 'm'), '');
  }

  writeFileSync(path, source);
}