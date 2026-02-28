#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');

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
    const headSha = process.env.HEAD_SHA;
    const headRef = process.env.HEAD_REF;
    const parentIssue = process.env.PARENT_ISSUE || '';
    const taskKey = process.env.TASK_KEY || '';
    const baseRef = process.env.BASE_REF || '';
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');
    const githubRef = process.env.GITHUB_REF || '';

    if (!token || !prNumber || !headSha || !headRef || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const config = loadConfig();
    const fallbackBaseBranch = config.copilot.base_branch || 'main';
    const ref = githubRef || `refs/heads/${fallbackBaseBranch}`;

    const github = new GitHubClient(token, owner, repo);
    const dispatchRef = resolveDispatchRef(baseRef, ref, fallbackBaseBranch);

    await github.createWorkflowDispatch(
      'agent-ci.yml',
      dispatchRef,
      {
        pr_number: prNumber.toString(),
        head_sha: headSha,
        head_ref: headRef
      }
    );

    core.info(`✓ Triggered CI for PR #${prNumber}`);

    if (parentIssue && taskKey) {
      await github.createWorkflowDispatch(
        'agent-merge-policy.yml',
        dispatchRef,
        {
          pr_number: prNumber.toString(),
          parent_issue: parentIssue,
          task_key: taskKey
        }
      );

      core.info(`✓ Triggered merge policy evaluation for PR #${prNumber}`);
    }
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  resolveDispatchRef,
  main
};
