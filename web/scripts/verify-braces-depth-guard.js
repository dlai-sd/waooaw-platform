const braces = require('/opt/waooaw-web/node_modules/.pnpm/node_modules/braces');

const nestedBraces = `${'{'.repeat(3500)}x${'}'.repeat(3500)}`;
const nestedParentheses = `${'('.repeat(3500)}x${')'.repeat(3500)}`;

for (const pattern of [nestedBraces, nestedParentheses]) {
  try {
    braces(pattern);
  } catch (error) {
    if (error instanceof SyntaxError && error.message.includes('nesting depth')) {
      continue;
    }
    throw error;
  }
  throw new Error('braces depth guard accepted a stack-exhaustion pattern');
}

if (braces('a/{b,c}/d')[0] !== 'a/(b|c)/d') {
  throw new Error('braces depth guard changed ordinary pattern behavior');
}
