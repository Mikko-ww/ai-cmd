#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { StateManager } = require('./lib/state-manager');
const { loadPrompt } = require('./lib/prompt-loader');
const { loadPlanOrFail } = require('./lib/plan-contract');
const { parsePositiveIntegerStrict, normalizeModelName, displayModelName } = require('./lib/utils');

const VALID_LEVELS = new Set(['l1', 'l2', 'l3']);
const VALID_STATUSES = new Set(['pending', 'in-progress', 'in-review', 'blocked', 'done', 'cancelled']);
const ACTIVE_STATUSES = new Set(['in-progress', 'in-review']);

function normalizeTaskLevel(level, taskId) {
  const normalized = String(level || '').trim().toLowerCase();
  if (!VALID_LEVELS.has(normalized)) {
    throw new Error(`Invalid task level for ${taskId}: ${level}. Expected one of: l1, l2, l3`);
  }
  return normalized;
}

function normalizeStatus(status) {
  const normalized = String(status || '').trim().toLowerCase();
  if (!VALID_STATUSES.has(normalized)) {
    return null;
  }
  return normalized;
}

function normalizePositiveInteger(value) {
  if (Number.isInteger(value) && value > 0) {
    return value;
  }
  return null;
}

function buildRiskNotes(taskLevel) {
  if (taskLevel === 'l1') {
    return '- This is a low-risk task (docs/tests only)\n- Will auto-merge after CI passes';
  }

  if (taskLevel === 'l2') {
    return '- This is a medium-risk task\n- Requires `/approve-task` command after CI passes';
  }

  return '- This is a high-risk task\n- Requires full PR review before merge';
}

function resolveTaskModel(taskModel, fallbackModel) {
  const normalizedTaskModel = normalizeModelName(taskModel);
  if (normalizedTaskModel) {
    return normalizedTaskModel;
  }

  return normalizeModelName(fallbackModel);
}

function ensureRuntimeTask(state, taskDef, now, defaultModel) {
  const runtime = state.tasks[taskDef.id] || {};

  const normalizedLevel = normalizeTaskLevel(taskDef.level, taskDef.id);
  const normalizedStatus = normalizeStatus(runtime.status) || 'pending';

  const merged = {
    task_key: taskDef.id,
    title: taskDef.title,
    level: normalizedLevel,
    model: resolveTaskModel(taskDef.model, runtime.model || defaultModel),
    deps: Array.isArray(taskDef.deps) ? taskDef.deps.slice() : [],
    acceptance: taskDef.acceptance,
    issue_number: normalizePositiveInteger(runtime.issue_number),
    pr_number: normalizePositiveInteger(runtime.pr_number),
    status: normalizedStatus,
    created_at: runtime.created_at || now,
    updated_at: runtime.updated_at || now
  };

  state.tasks[taskDef.id] = merged;
  return merged;
}

function depsSatisfied(taskRuntime, runtimeMap) {
  for (const depId of taskRuntime.deps) {
    const dep = runtimeMap[depId];
    if (!dep || dep.status !== 'done') {
      return false;
    }
  }
  return true;
}

function hasOnlyFinalStatuses(runtimeTasks) {
  return runtimeTasks.every((task) => task.status === 'done' || task.status === 'cancelled');
}

async function markParentDone(github, config, issueNumber) {
  await github.removeLabel(issueNumber, config.labels.parent.executing);
  await github.addLabels(issueNumber, [config.labels.parent.done]);
  await github.createComment(
    issueNumber,
    '🎉 All Tasks Completed\n\nAll tasks have been completed and merged.\n\nStatus: `done`'
  );
}

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const issueNumber = parsePositiveIntegerStrict('PARENT_ISSUE', process.env.PARENT_ISSUE);
    const [owner, repo] = (process.env.GITHUB_REPOSITORY || '').split('/');

    if (!token || !issueNumber || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();
    const defaultModel = normalizeModelName(config.copilot?.model);
    const now = new Date().toISOString();

    const stateManager = new StateManager(github, issueNumber);
    await stateManager.load();

    if (stateManager.state.paused) {
      core.info('⏸️ Dispatch paused');
      return;
    }

    if (!stateManager.state.tasks || typeof stateManager.state.tasks !== 'object') {
      stateManager.state.tasks = {};
    }

    const planPath = `${config.paths.plan_yaml_dir}/issue-${issueNumber}.yaml`;
    const plan = loadPlanOrFail(planPath, { mode: 'strict' });

    const runtimeById = {};
    for (const task of plan.tasks) {
      runtimeById[task.id] = ensureRuntimeTask(stateManager.state, task, now, defaultModel);
    }

    const runtimeTasks = plan.tasks.map((task) => runtimeById[task.id]);
    const activeTask = runtimeTasks.find((task) => ACTIVE_STATUSES.has(task.status));

    if (activeTask) {
      core.info(`⏳ Task ${activeTask.task_key} is already active (${activeTask.status})`);
      return;
    }

    if (hasOnlyFinalStatuses(runtimeTasks)) {
      stateManager.state.cursor_task_id = null;
      stateManager.state.revision += 1;
      stateManager.state.updated_at = now;
      await stateManager.save();
      await markParentDone(github, config, issueNumber);
      core.info('✅ All tasks completed');
      return;
    }

    const nextTaskDef = plan.tasks.find((task) => {
      const runtime = runtimeById[task.id];
      return runtime.status === 'pending' && depsSatisfied(runtime, runtimeById);
    });

    if (!nextTaskDef) {
      core.info('⏳ No dispatchable pending task (dependencies not satisfied or tasks blocked)');
      return;
    }

    const nextRuntime = runtimeById[nextTaskDef.id];
    if (!nextRuntime.issue_number) {
      throw new Error(`Task ${nextRuntime.task_key} has no associated issue_number in runtime state`);
    }

    const taskIssue = await github.getIssue(nextRuntime.issue_number);

    await github.removeLabel(nextRuntime.issue_number, config.labels.task.pending);
    await github.removeLabel(nextRuntime.issue_number, config.labels.task.in_review);
    await github.removeLabel(nextRuntime.issue_number, config.labels.task.blocked);
    await github.addLabels(nextRuntime.issue_number, [config.labels.task.in_progress]);

    const customInstructions = loadPrompt('dispatch/task', {
      taskKey: nextRuntime.task_key,
      taskLevel: nextRuntime.level,
      taskLevelUpper: nextRuntime.level.toUpperCase(),
      taskTitle: nextRuntime.title,
      acceptance: nextRuntime.acceptance || 'No specific acceptance criteria',
      parentIssue: issueNumber,
      riskNotes: buildRiskNotes(nextRuntime.level),
      baseBranch: config.copilot.base_branch,
      taskIssue: nextRuntime.issue_number,
      taskBody: taskIssue.body || 'No description provided',
      taskModel: displayModelName(nextRuntime.model)
    });
    const assignmentModel = resolveTaskModel(nextRuntime.model, defaultModel);

    await github.updateIssue(nextRuntime.issue_number, {
      assignees: [config.copilot.bot_assignee],
      agent_assignment: {
        target_repo: `${owner}/${repo}`,
        base_branch: config.copilot.base_branch,
        custom_instructions: customInstructions,
        custom_agent: '',
        model: assignmentModel
      }
    });

    nextRuntime.status = 'in-progress';
    nextRuntime.updated_at = now;

    stateManager.state.cursor_task_id = nextRuntime.task_key;
    stateManager.state.revision += 1;
    stateManager.state.updated_at = now;
    await stateManager.save();

    await github.createComment(
      issueNumber,
      [
        '🚀 Task Dispatched',
        '',
        `Assigned task ${nextRuntime.task_key} to ${config.copilot.bot_assignee}`,
        '',
        `- Task: ${nextRuntime.title}`,
        `- Issue: #${nextRuntime.issue_number}`,
        `- Level: ${nextRuntime.level}`,
        `- Model: ${displayModelName(assignmentModel)}`,
        '',
        'Status: `in-progress`'
      ].join('\n')
    );

    core.info(`✓ Dispatched task ${nextRuntime.task_key} to Copilot`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
