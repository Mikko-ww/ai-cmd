#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const issueNumber = parseInt(process.env.ISSUE_NUMBER);
    const labels = process.env.LABELS ? process.env.LABELS.split(',').map(l => l.trim()) : [];
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !issueNumber || !owner || !repo || labels.length === 0) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    await github.addLabels(issueNumber, labels);

    core.info(`✓ Added labels: ${labels.join(', ')}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
