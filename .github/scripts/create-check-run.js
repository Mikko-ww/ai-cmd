#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');

async function main() {
  try {
    const token = process.env.GITHUB_TOKEN;
    const headSha = process.env.HEAD_SHA;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !headSha || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    const check = await github.createCheckRun('agent/ci', headSha, 'in_progress');

    core.setOutput('check_run_id', check.data.id);
    core.info(`✓ Check run created: ${check.data.id}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
