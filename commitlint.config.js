// commitlint.config.js
// Enforces conventional commit format on all commits.
// Constitutional basis: engineering-standards.md §4 (Commit Convention)
// Run: npx commitlint --edit $1 (add as .git/hooks/commit-msg)
//
// Install: npm install --save-dev @commitlint/cli @commitlint/config-conventional
// Git hook: npx husky add .husky/commit-msg 'npx --no -- commitlint --edit ${1}'

module.exports = {
  extends: ['@commitlint/config-conventional'],

  rules: {
    // Standard types + WAOOAW-specific types
    'type-enum': [
      2, 'always', [
        'feat',           // new feature
        'fix',            // bug fix
        'constitutional', // implements a constitutional principle (C-NNN or AD-NNN)
        'cct',            // adds or fixes a Constitutional Compliance Test
        'security',       // security fix or improvement
        'docs',           // documentation only
        'refactor',       // code change without feature or fix
        'perf',           // performance improvement
        'test',           // adding or correcting tests
        'chore',          // maintenance (deps, config, tooling)
        'ci',             // CI/CD pipeline changes
        'revert',         // reverts a previous commit
      ]
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

    // Subject: lowercase, no period at end, max 100 chars
    'subject-case': [2, 'always', 'lower-case'],
    'subject-full-stop': [2, 'never', '.'],
    'subject-max-length': [2, 'always', 100],

    // Body: optional but if present must have blank line before it
    'body-leading-blank': [2, 'always'],

    // Footer: optional but if present must have blank line before it
    'footer-leading-blank': [2, 'always'],
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
