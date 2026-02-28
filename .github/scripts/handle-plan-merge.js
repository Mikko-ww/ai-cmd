#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { loadPlanOrFail, formatValidationError } = require('./lib/plan-contract');
const { PHASES, updatePhaseStatus, getPhaseIssue } = require('./lib/phase-manager');
const { StateManager } = require('./lib/state-manager');

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
    const epicIssueNumber = parseInt(process.env.PARENT_ISSUE);
    const baseRef = process.env.BASE_REF || '';
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');
    const ref = process.env.GITHUB_REF || 'refs/heads/main';

    if (!token || !epicIssueNumber || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();

    const stateManager = new StateManager(github, epicIssueNumber);
    await stateManager.load();

    const planIssueNumber = getPhaseIssue(stateManager.state, PHASES.PLAN);
    const planPath = `${config.paths.plan_yaml_dir}/issue-${epicIssueNumber}.yaml`;

    try {
      loadPlanOrFail(planPath, { mode: 'strict' });
    } catch (error) {
      const payload = formatValidationError(error);

      await updatePhaseStatus(stateManager.state, PHASES.PLAN, 'failed', {
        validation_error: {
          code: payload.code,
          path: payload.path,
          message: payload.message
        }
      });

      await stateManager.save();

      await github.addLabels(epicIssueNumber, [config.labels.parent.blocked]);
      await github.createComment(epicIssueNumber, [
        '❌ **Plan Validation Failed**',
        '',
        `Validation gate blocked execution for plan file: \`${planPath}\``,
        '',
        `- Code: \`${payload.code}\``,
        `- Path: \`${payload.path}\``,
        `- Message: ${payload.message}`,
        payload.hint ? `- Hint: ${payload.hint}` : '',
        '',
        'Please fix plan YAML and rerun the plan phase.'
      ].filter(Boolean).join('\n'));

      throw new Error(`Plan validation gate failed: ${payload.code}`);
    }

    if (planIssueNumber) {
      await github.updateIssue(planIssueNumber, { state: 'closed' });
      core.info(`Closed Plan Issue #${planIssueNumber}`);
    }

    await updatePhaseStatus(stateManager.state, PHASES.PLAN, 'done', {
      completed_at: new Date().toISOString()
    });

    stateManager.state.current_phase = PHASES.EXECUTION;

    await stateManager.save();

    await github.createComment(epicIssueNumber, [
      '✅ **Plan Phase Complete**',
      '',
      'The execution plan has been approved and merged.',
      '',
      '**Next Phase:** Task Execution',
      '- Creating task sub-issues...',
      '- Tasks will be assigned to Copilot for implementation',
      '',
      '**Workflow Progress:**',
      '- ✅ Specification',
      '- ✅ Execution Plan',
      '- 🔄 Implementation (starting)'
    ].join('\n'));

    const dispatchRef = resolveDispatchRef(baseRef, ref, config.copilot.base_branch);

    await github.createWorkflowDispatch(
      'agent-task-creator.yml',
      dispatchRef,
      { parent_issue: epicIssueNumber.toString() }
    );

    core.info('✓ Plan merge handled, triggered task creation');
  } catch (error) {
    core.setFailed(`Failed to handle plan merge: ${error.message}`);
    process.exit(1);
  }
}

main();
