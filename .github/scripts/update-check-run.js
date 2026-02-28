#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');

async function main() {
  try {
    const token = process.env.GITHUB_TOKEN;
    const checkRunId = parseInt(process.env.CHECK_RUN_ID);
    const validateSuccess = process.env.VALIDATE_SUCCESS === 'true';
    const lintSuccess = process.env.LINT_SUCCESS === 'true';
    const testSuccess = process.env.TEST_SUCCESS === 'true';
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !checkRunId || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    let conclusion = 'success';
    let summary = '✓ All checks passed';
    let text = '';

    if (!validateSuccess) {
      conclusion = 'failure';
      summary = '✗ PR parameter validation failed';
      text = 'The PR head SHA or ref does not match the expected values. This may indicate the PR was updated after CI was triggered.';
    } else if (!lintSuccess || !testSuccess) {
      conclusion = 'failure';
      summary = '✗ CI checks failed';
      text = '';

      if (!lintSuccess) {
        text += '**Lint:** Failed\n\n';
      } else {
        text += '**Lint:** Passed\n\n';
      }

      if (!testSuccess) {
        text += '**Tests:** Failed\n\n';
      } else {
        text += '**Tests:** Passed\n\n';
      }

      text += '\nPlease fix the failing checks and push updates to the PR.';
    } else {
      text = '**Lint:** Passed\n**Tests:** Passed\n\nAll CI checks completed successfully.';
    }

    await github.updateCheckRun(checkRunId, 'completed', conclusion, {
      title: 'Agent CI Verification',
      summary: summary,
      text: text
    });

    core.info(`✓ Check run updated: ${conclusion}`);

    if (conclusion === 'failure') {
      core.setFailed(summary);
    }
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
