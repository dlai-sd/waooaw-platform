"use strict";

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const validateSecurityPatches = (webRoot) => {
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(webRoot, "package.json"), "utf8"),
  );
  const policy = JSON.parse(
    fs.readFileSync(path.join(webRoot, "security-patches.json"), "utf8"),
  );
  const lockfile = fs.readFileSync(
    path.join(webRoot, "pnpm-lock.yaml"),
    "utf8",
  );

  if (
    policy.schema !== "waooaw.web-security-patches/v1" ||
    !Array.isArray(policy.advisories)
  ) {
    throw new Error("invalid Web security patch policy");
  }

  const ignored = packageJson.pnpm?.auditConfig?.ignoreGhsas;
  const patchedDependencies = packageJson.pnpm?.patchedDependencies;
  if (
    !Array.isArray(ignored) ||
    typeof patchedDependencies !== "object" ||
    patchedDependencies === null
  ) {
    throw new Error(
      "pnpm audit exceptions require patchedDependencies and ignoreGhsas",
    );
  }

  const policyGhsas = policy.advisories.map(({ ghsa }) => ghsa);
  if (new Set(policyGhsas).size !== policyGhsas.length) {
    throw new Error("security patch policy contains duplicate advisories");
  }
  if (
    JSON.stringify([...ignored].sort()) !==
    JSON.stringify([...policyGhsas].sort())
  ) {
    throw new Error(
      "every ignored GHSA must have exactly one security patch policy entry",
    );
  }

  const resolvePolicyPath = (relativePath, field) => {
    if (typeof relativePath !== "string" || path.isAbsolute(relativePath)) {
      throw new Error(`${field} must be relative to the Web root`);
    }
    const resolved = path.resolve(webRoot, relativePath);
    if (
      !resolved.startsWith(`${webRoot}${path.sep}`) ||
      !fs.existsSync(resolved) ||
      !fs.statSync(resolved).isFile()
    ) {
      throw new Error(`${field} must identify a file inside the Web root`);
    }
    return resolved;
  };

  for (const advisory of policy.advisories) {
    const dependency = `${advisory.package}@${advisory.version}`;
    const patch = resolvePolicyPath(advisory.patch, "patch");
    const verifier = resolvePolicyPath(advisory.verifier, "verifier");
    if (patchedDependencies[dependency] !== advisory.patch) {
      throw new Error(`${advisory.ghsa} is not bound to ${dependency}`);
    }
    if (
      !lockfile.includes(`${dependency}:`) ||
      !lockfile.includes(`path: ${advisory.patch}`)
    ) {
      throw new Error(
        `${advisory.ghsa} patch is absent from the frozen lockfile`,
      );
    }
    if (fs.readFileSync(patch, "utf8").trim() === "") {
      throw new Error(`${advisory.ghsa} patch is empty`);
    }
    const verification = spawnSync(process.execPath, [verifier], {
      cwd: webRoot,
      stdio: "inherit",
    });
    if (verification.status !== 0) {
      throw new Error(`${advisory.ghsa} exploit regression failed`);
    }
  }
};

if (require.main === module) {
  validateSecurityPatches(path.resolve(__dirname, ".."));
}

module.exports = { validateSecurityPatches };
