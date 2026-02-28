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

function resolveDispatchRef(baseRef, githubRef, fallbackRef) {
  if (baseRef && typeof baseRef === 'string') {
    return baseRef;
  }

  if (githubRef && githubRef.startsWith('refs/heads/')) {
    return githubRef.replace('refs/heads/', '');
  }

  return fallbackRef;
}

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const prNumber = parseInt(process.env.PR_NUMBER, 10);
    const parentIssue = parseInt(process.env.PARENT_ISSUE, 10);
    const taskKey = process.env.TASK_KEY;
    const githubRef = process.env.GITHUB_REF || '';
    const baseRef = process.env.BASE_REF || '';
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !prNumber || !parentIssue || !taskKey || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();

    const pr = await github.getPR(prNumber);
    if (!pr.merged) {
      core.info(`PR #${prNumber} is closed but not merged. Skip task completion.`);
      return;
    }

    const stateManager = new StateManager(github, parentIssue);
    await stateManager.load();

    if (!stateManager.state.tasks || typeof stateManager.state.tasks !== 'object') {
      throw new Error(`State.tasks is missing for parent issue #${parentIssue}`);
    }

    const runtime = stateManager.state.tasks[taskKey];
    if (!runtime) {
      throw new Error(`Task runtime not found for ${taskKey}. Cannot finalize merged PR.`);
    }

    const now = new Date().toISOString();
    runtime.pr_number = prNumber;
    runtime.status = 'done';
    runtime.updated_at = now;

    if (stateManager.state.cursor_task_id === taskKey) {
      stateManager.state.cursor_task_id = null;
    }

    stateManager.state.revision += 1;
    stateManager.state.updated_at = now;
    await stateManager.save();

    const issueNumber = normalizePositiveInteger(runtime.issue_number);
    if (issueNumber) {
      await github.removeLabel(issueNumber, config.labels.task.pending);
      await github.removeLabel(issueNumber, config.labels.task.in_progress);
      await github.removeLabel(issueNumber, config.labels.task.in_review);
      await github.removeLabel(issueNumber, config.labels.task.blocked);
      await github.removeLabel(issueNumber, config.labels.task.cancelled);
      await github.addLabels(issueNumber, [config.labels.task.done]);

      const issue = await github.getIssue(issueNumber);
      if (issue.state !== 'closed') {
        await github.updateIssue(issueNumber, { state: 'closed' });
      }
    }

    await github.createComment(
      parentIssue,
      `✅ Task completed: ${taskKey} via PR #${prNumber}. Dispatching next task...`
    );

    const dispatchRef = resolveDispatchRef(baseRef, githubRef, config.copilot.base_branch);
    await github.createWorkflowDispatch('agent-task-dispatcher.yml', dispatchRef, {
      parent_issue: parentIssue.toString(),
      trigger: 'task-merged'
    });

    core.info(`✓ Task ${taskKey} marked done from PR #${prNumber}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
