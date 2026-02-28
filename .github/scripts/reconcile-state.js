#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { StateManager } = require('./lib/state-manager');

const ACTIVE_STATUSES = new Set(['in-progress', 'in-review']);

function normalizePositiveInteger(value) {
  if (Number.isInteger(value) && value > 0) {
    return value;
  }
  return null;
}

function resolveDispatchRef(githubRef, fallbackRef) {
  if (githubRef && githubRef.startsWith('refs/heads/')) {
    return githubRef.replace('refs/heads/', '');
  }
  return fallbackRef;
}

async function markTaskIssueDone(github, config, issueNumber) {
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

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');
    const ref = process.env.GITHUB_REF || 'refs/heads/main';

    if (!token || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();
    const dispatchRef = resolveDispatchRef(ref, config.copilot.base_branch);

    const issues = await github.listIssues({
      state: 'open',
      labels: config.labels.parent.executing,
      perPage: 100
    });

    let reconciledCount = 0;

    for (const issue of issues) {
      try {
        const stateManager = new StateManager(github, issue.number);
        await stateManager.load();

        const runtimeTasks = stateManager.state.tasks || {};
        const now = new Date().toISOString();
        let changed = false;

        for (const [taskKey, runtime] of Object.entries(runtimeTasks)) {
          if (!runtime || !ACTIVE_STATUSES.has(runtime.status)) {
            continue;
          }

          const prNumber = normalizePositiveInteger(runtime.pr_number);
          if (!prNumber) {
            continue;
          }

          const pr = await github.getPR(prNumber).catch(() => null);
          if (!pr || !pr.merged) {
            continue;
          }

          runtime.status = 'done';
          runtime.updated_at = now;

          const taskIssueNumber = normalizePositiveInteger(runtime.issue_number);
          if (taskIssueNumber) {
            await markTaskIssueDone(github, config, taskIssueNumber);
          }

          await github.createComment(
            issue.number,
            `🔄 Reconciliation: task ${taskKey} marked done from merged PR #${prNumber}.`
          );

          reconciledCount += 1;
          changed = true;
        }

        if (!changed) {
          continue;
        }

        stateManager.state.revision += 1;
        stateManager.state.updated_at = now;
        await stateManager.save();

        await github.createWorkflowDispatch('agent-task-dispatcher.yml', dispatchRef, {
          parent_issue: issue.number.toString(),
          trigger: 'reconcile'
        });

        core.info(`✓ Reconciled issue #${issue.number}`);
      } catch (error) {
        core.warning(`Failed to reconcile issue #${issue.number}: ${error.message}`);
      }
    }

    core.info(`✓ Reconciliation complete: ${reconciledCount} tasks reconciled`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
