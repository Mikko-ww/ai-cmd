#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { createInitialState } = require('./lib/state-manager');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const issueNumber = parseInt(process.env.ISSUE_NUMBER);
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !issueNumber || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();
    const stateMarker = config.state.marker;
    const initialState = createInitialState(issueNumber, owner, repo);

    // Create state comment
    const stateComment = [
      stateMarker,
      '```json',
      JSON.stringify(initialState, null, 2),
      '```',
      '',
      'Agent State Initialized',
      '',
      'This comment tracks the execution state of the autonomous agent. Do not edit manually.'
    ].join('\n');

    await github.createComment(issueNumber, stateComment);

    core.info(`✓ State initialized for issue #${issueNumber}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
