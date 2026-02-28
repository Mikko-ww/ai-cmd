#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { PHASES, updatePhaseStatus, getPhaseIssue } = require('./lib/phase-manager');
const { StateManager } = require('./lib/state-manager');

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const epicIssueNumber = parseInt(process.env.PARENT_ISSUE);
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');

    if (!token || !epicIssueNumber || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);

    const stateManager = new StateManager(github, epicIssueNumber);
    await stateManager.load();

    const specIssueNumber = getPhaseIssue(stateManager.state, PHASES.SPEC);
    
    if (specIssueNumber) {
      await github.updateIssue(specIssueNumber, { state: 'closed' });
      core.info(`Closed Spec Issue #${specIssueNumber}`);
    }

    await updatePhaseStatus(stateManager.state, PHASES.SPEC, 'done', {
      completed_at: new Date().toISOString()
    });

    await stateManager.save();

    const { execSync } = require('child_process');
    execSync(`node ${__dirname}/create-phase-issue.js`, {
      env: {
        ...process.env,
        PHASE: PHASES.PLAN,
        EPIC_ISSUE: epicIssueNumber.toString()
      },
      stdio: 'inherit'
    });

    await github.createComment(epicIssueNumber, [
      '✅ **Specification Phase Complete**',
      '',
      'The specification has been approved and merged.',
      '',
      '**Next Phase:** Execution Plan (执行计划)',
      '- A new Plan Issue has been created',
      '- Copilot will generate the execution plan',
      '',
      '**Workflow Progress:**',
      '- ✅ Specification',
      '- 🔄 Execution Plan (in progress)',
      '- ⏳ Implementation'
    ].join('\n'));

    core.info('✓ Spec merge handled successfully');
  } catch (error) {
    core.setFailed(`Failed to handle spec merge: ${error.message}`);
    process.exit(1);
  }
}

main();
