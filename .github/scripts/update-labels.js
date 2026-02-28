#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const issueNumber = parseInt(process.env.ISSUE_NUMBER);
    const removeLabels = process.env.REMOVE_LABELS ? process.env.REMOVE_LABELS.split(',').map(l => l.trim()) : [];
    const addLabels = process.env.ADD_LABELS ? process.env.ADD_LABELS.split(',').map(l => l.trim()) : [];
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !issueNumber || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    if (removeLabels.length === 0 && addLabels.length === 0) {
      core.setFailed('No labels to add or remove');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    if (removeLabels.length > 0) {
      for (const label of removeLabels) {
        try {
          await github.removeLabel(issueNumber, label);
          core.info(`✓ Removed label: ${label}`);
        } catch (error) {
          core.warning(`Failed to remove label ${label}: ${error.message}`);
        }
      }
    }

    if (addLabels.length > 0) {
      await github.addLabels(issueNumber, addLabels);
      core.info(`✓ Added labels: ${addLabels.join(', ')}`);
    }

    core.info('✓ Labels updated successfully');
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
