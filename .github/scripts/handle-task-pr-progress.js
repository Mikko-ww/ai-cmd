#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { StateManager } = require('./lib/state-manager');

function normalizePositiveInteger(value) {
  if (Number.isInteger(value) && value > 0) {
    return value;
  }
  return null;
}

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const prNumber = parseInt(process.env.PR_NUMBER, 10);
    const parentIssue = parseInt(process.env.PARENT_ISSUE, 10);
    const taskKey = process.env.TASK_KEY;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !prNumber || !parentIssue || !taskKey || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();
    const stateManager = new StateManager(github, parentIssue);
    await stateManager.load();

    if (!stateManager.state.tasks || typeof stateManager.state.tasks !== 'object') {
      throw new Error(`State.tasks is missing for parent issue #${parentIssue}`);
    }

    const runtime = stateManager.state.tasks[taskKey];
    if (!runtime) {
      throw new Error(`Task runtime not found for ${taskKey}. Run task creator first.`);
    }

    const previousStatus = runtime.status;
    const previousPrNumber = normalizePositiveInteger(runtime.pr_number);
    const nextStatus = previousStatus === 'done' || previousStatus === 'cancelled' ? previousStatus : 'in-review';
    const nextPrNumber = prNumber;

    if (previousStatus === nextStatus && previousPrNumber === nextPrNumber) {
      core.info(`Task runtime already up to date for ${taskKey}`);
      return;
    }

    const now = new Date().toISOString();
    runtime.pr_number = nextPrNumber;
    runtime.status = nextStatus;
    runtime.updated_at = now;

    if (nextStatus === 'in-review') {
      stateManager.state.cursor_task_id = taskKey;
    }

    stateManager.state.revision += 1;
    stateManager.state.updated_at = now;
    await stateManager.save();

    const issueNumber = normalizePositiveInteger(runtime.issue_number);
    if (issueNumber && nextStatus === 'in-review') {
      await github.removeLabel(issueNumber, config.labels.task.pending);
      await github.removeLabel(issueNumber, config.labels.task.in_progress);
      await github.removeLabel(issueNumber, config.labels.task.blocked);
      await github.addLabels(issueNumber, [config.labels.task.in_review]);
    }

    core.info(`✓ Updated task runtime for ${taskKey}: pr_number=${nextPrNumber}, status=${nextStatus}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
