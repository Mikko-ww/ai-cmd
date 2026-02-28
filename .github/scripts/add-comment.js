#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const issueNumber = parseInt(process.env.ISSUE_NUMBER);
    const commentBody = process.env.COMMENT_BODY;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !issueNumber || !commentBody || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    await github.createComment(issueNumber, commentBody);

    core.info(`✓ Added comment to issue #${issueNumber}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
