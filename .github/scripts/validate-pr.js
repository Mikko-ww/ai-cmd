#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { parsePositiveIntegerStrict } = require('./lib/utils');

async function main() {
  try {
    const token = process.env.GITHUB_TOKEN;
    const prNumber = parsePositiveIntegerStrict('PR_NUMBER', process.env.PR_NUMBER);
    const headSha = process.env.HEAD_SHA;
    const headRef = process.env.HEAD_REF;
    const [owner, repo] = (process.env.GITHUB_REPOSITORY || '').split('/');

    if (!token || !prNumber || !headSha || !headRef || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    const pr = await github.getPR(prNumber);

    if (pr.head.sha !== headSha) {
      core.setFailed(`PR head SHA mismatch: expected ${headSha}, got ${pr.head.sha}`);
      return;
    }

    if (pr.head.ref !== headRef) {
      core.setFailed(`PR head ref mismatch: expected ${headRef}, got ${pr.head.ref}`);
      return;
    }

    core.info(`✓ PR parameters validated: #${prNumber} @ ${headSha}`);
    core.setOutput('valid', 'true');
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
