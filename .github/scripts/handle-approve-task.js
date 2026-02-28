#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const prNumber = parseInt(process.env.PR_NUMBER);
    const approver = process.env.APPROVER;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !prNumber || !approver || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();

    const pr = await github.getPR(prNumber);
    const labels = pr.labels.map(l => l.name);

    if (!labels.includes(config.labels.level.l2)) {
      await github.createComment(
        prNumber,
        '❌ `/approve-task` can only be used on L2 task PRs.'
      );
      return;
    }

    const checkRuns = await github.listCheckRuns(pr.head.sha);

    const ciCheck = checkRuns.find(c => c.name === config.ci.required_check_name);
    if (!ciCheck || ciCheck.conclusion !== 'success') {
      await github.createComment(
        prNumber,
        '❌ Cannot approve: CI checks have not passed yet.'
      );
      return;
    }

    try {
      await github.mergePR(prNumber, 'squash');

      await github.createComment(
        prNumber,
        `✅ **Task Approved and Merged**\n\nApproved by @${approver}`
      );

      core.info(`✓ PR #${prNumber} approved and merged`);
    } catch (error) {
      await github.createComment(
        prNumber,
        `❌ **Merge Failed**\n\n${error.message}`
      );
      throw error;
    }
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
