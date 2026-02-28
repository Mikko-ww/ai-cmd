#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { parsePositiveIntegerStrict } = require('./lib/utils');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const prNumber = parsePositiveIntegerStrict('PR_NUMBER', process.env.PR_NUMBER);
    const [owner, repo] = (process.env.GITHUB_REPOSITORY || '').split('/');

    if (!token || !prNumber || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();

    try {
      await github.mergePR(prNumber, 'squash');
      core.info('✓ PR auto-merged (L1)');
    } catch (error) {
      if (error.status === 405 && error.message.includes('auto-merge')) {
        core.warning('Auto-merge not available, downgrading to L2');

        await github.removeLabel(prNumber, 'agent:l1');
        await github.addLabels(prNumber, ['agent:l2']);

        await github.createComment(prNumber, [
          '⚠️ Auto-merge Downgrade',
          '',
          'This PR was classified as L1 but auto-merge is not available (repository settings or branch protection).',
          '',
          'Downgraded to L2: Please use `/approve-task` command to merge.'
        ].join('\n'));
      } else {
        core.warning(`Auto-merge failed: ${error.message}`);
        throw error;
      }
    }
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
