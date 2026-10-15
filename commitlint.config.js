// commitlint.config.js
// Enforces conventional commit format on all commits.
// Constitutional basis: engineering-standards.md §4 (Commit Convention)
// Run: npx commitlint --edit $1 (add as .git/hooks/commit-msg)
//
// Install: npm install --save-dev @commitlint/cli @commitlint/config-conventional
// Git hook: npx husky add .husky/commit-msg 'npx --no -- commitlint --edit ${1}'

const commitPolicy = require('./validation/commit-message-policy.json');

module.exports = {
  extends: ['@commitlint/config-conventional'],

  rules: {
    // Standard types + WAOOAW-specific types
    'type-enum': [
      2, 'always', commitPolicy.types
    ],

    // Scope must be one of the known service/domain scopes
    'scope-enum': [
      1, 'always', [
        'ce',    // Constitutional Engine
        'bp',    // Business Platform
        'pr',    // Professional Runtime
        'ai',    // AI Runtime
        'web',   // Web App
        'infra', // Infrastructure (postgres, keycloak, temporal)
        'db',    // Database migrations
        'cct',   // Constitutional Compliance Tests
        'adr',   // Architecture Decision Records
        'arch',  // Architecture reference docs
        'ci',    // CI/CD pipeline
        'ops',   // Platform operations
        'pm',    // Platform Delivery Tracker / PM workflows
      ]
    ],

    // Subject: reject title/sentence casing while permitting stable acronyms.
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'subject-full-stop': [2, 'never', '.'],
    'subject-max-length': [2, 'always', commitPolicy.subject_max_length],

    // Body: optional but if present must have blank line before it
    'body-leading-blank': [2, 'always'],
    'body-max-line-length': [2, 'always', commitPolicy.body_max_line_length],

    // Footer: optional but if present must have blank line before it
    'footer-leading-blank': [2, 'always'],
    'footer-max-line-length': [2, 'always', commitPolicy.footer_max_line_length],
  },

  // Custom prompt for commitlint interactive mode
  prompt: {
    questions: {
      type: {
        description: 'Select commit type (constitutional = implements a constitutional principle):',
      },
      scope: {
        description: 'Service/scope affected (ce|bp|pr|ai|web|infra|db|cct|adr|arch|ci):',
      },
      subject: {
        description: 'Short description (lowercase, no period):',
      },
      body: {
        description: 'Longer description (optional). Include constitutional basis for constitutional commits:',
      },
    },
  },
};
