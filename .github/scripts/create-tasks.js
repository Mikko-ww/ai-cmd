#!/usr/bin/env node

const core = require('@actions/core');
const fs = require('fs');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');
const { tryParseAgentMetadata, buildMarkerBlock, schema } = require('./lib/marker-parser');
const { loadPlanOrFail } = require('./lib/plan-contract');
const { StateManager } = require('./lib/state-manager');
const { parsePositiveIntegerStrict, normalizeModelName, displayModelName } = require('./lib/utils');

const TASK_KEY_PATTERN = new RegExp(schema.patterns.taskKey);
const VALID_LEVELS = new Set(['l1', 'l2', 'l3']);
const VALID_TASK_STATUSES = new Set(['pending', 'in-progress', 'in-review', 'blocked', 'done', 'cancelled']);

function normalizeTaskLevel(level, taskKey) {
  const normalized = String(level || '').trim().toLowerCase();
  if (!VALID_LEVELS.has(normalized)) {
    throw new Error(`Invalid task level for ${taskKey}: ${level}. Expected one of: l1, l2, l3`);
  }
  return normalized;
}

function resolveTaskModel(taskModel, fallbackModel) {
  const normalizedTaskModel = normalizeModelName(taskModel);
  if (normalizedTaskModel) {
    return normalizedTaskModel;
  }

  return normalizeModelName(fallbackModel);
}

function slugifyTaskText(text) {
  return (text || 'untitled')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '') || 'untitled';
}

function enforceMaxLength(taskKey, suffix = '') {
  const maxLength = 64;
  const suffixLength = suffix.length;
  const baseMax = maxLength - suffixLength;
  if (taskKey.length <= maxLength) {
    return taskKey + suffix;
  }

  const truncated = taskKey.slice(0, baseMax).replace(/-+$/g, '');
  return `${truncated}${suffix}`;
}

function buildBaseTaskKey(rawId, title) {
  let base = typeof rawId === 'string' ? rawId.trim().toLowerCase() : '';

  if (!TASK_KEY_PATTERN.test(base)) {
    base = `task-${slugifyTaskText(title || rawId)}`;
  }

  return enforceMaxLength(base);
}

function allocateUniqueTaskKey(base, usedKeys) {
  if (!usedKeys.has(base)) {
    return base;
  }

  let index = 2;
  while (index < 1000) {
    const suffix = `-${index}`;
    const candidate = enforceMaxLength(base, suffix);
    if (!usedKeys.has(candidate)) {
      return candidate;
    }
    index += 1;
  }

  throw new Error(`Unable to generate unique task key for: ${base}`);
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
    const planPath = `${config.paths.plan_yaml_dir}/issue-${issueNumber}.yaml`;

    if (!fs.existsSync(planPath)) {
      core.setFailed(`Plan file not found: ${planPath}`);
      return;
    }

    const plan = loadPlanOrFail(planPath, { mode: 'strict' });

    const stateManager = new StateManager(github, issueNumber);
    await stateManager.load();

    if (!stateManager.state.tasks || typeof stateManager.state.tasks !== 'object') {
      stateManager.state.tasks = {};
    }

    const existingIssues = await github.listIssues({
      labels: config.labels.task.task,
      state: 'all',
      perPage: 100
    });

    const taskIssueMap = new Map();
    for (const issue of existingIssues) {
      const parsed = tryParseAgentMetadata(issue.body || '', 'issue');
      if (
        parsed.ok &&
        parsed.metadata.issueType === 'task' &&
        parsed.metadata.parentIssue === issueNumber &&
        parsed.metadata.taskKey
      ) {
        taskIssueMap.set(parsed.metadata.taskKey, issue);
      }
    }

    const createdIssues = [];
    const usedTaskKeys = new Set(taskIssueMap.keys());
    let createdCount = 0;
    const now = new Date().toISOString();

    for (const task of plan.tasks) {
      const baseTaskKey = buildBaseTaskKey(task.id, task.title);
      const taskKey = taskIssueMap.has(baseTaskKey)
        ? baseTaskKey
        : allocateUniqueTaskKey(baseTaskKey, usedTaskKeys);

      usedTaskKeys.add(taskKey);
      task.id = taskKey;
      task.level = normalizeTaskLevel(task.level, taskKey);
      task.model = resolveTaskModel(task.model, config.copilot?.model);

      let taskIssue = taskIssueMap.get(taskKey);
      let taskIssueNumber = taskIssue ? taskIssue.number : null;

      if (!taskIssueNumber) {
        const markerBlock = buildMarkerBlock({
          parentIssue: issueNumber,
          issueType: 'task',
          taskKey
        }, 'issue');

        const issueBody = [
          'Parent Issue: #' + issueNumber,
          'Task Key: `' + taskKey + '`',
          'Level: `' + task.level + '`',
          'Model: `' + displayModelName(task.model) + '`',
          'Plan: `' + planPath + '`',
          '',
          '## Task Description',
          '',
          task.title,
          '',
          '## Acceptance Criteria',
          '',
          task.acceptance || 'See plan file for details',
          '',
          '## Dependencies',
          '',
          task.deps && task.deps.length > 0 ? task.deps.map(d => '- ' + d).join('\n') : 'None',
          '',
          '## Notes',
          '',
          task.notes || 'None',
          '',
          '---',
          '',
          markerBlock
        ].join('\n');

        const newIssue = await github.createIssue(
          `[Task ${taskKey}] ${task.title}`,
          issueBody,
          [
            config.labels.task.task,
            config.labels.task.pending,
            config.labels.level[task.level]
          ]
        );

        taskIssueNumber = newIssue.number;
        taskIssue = newIssue;
        taskIssueMap.set(taskKey, newIssue);
        createdCount += 1;
        core.info(`✓ Created task issue #${taskIssueNumber} for ${taskKey}`);
      } else {
        core.info(`✓ Task issue #${taskIssueNumber} already exists for ${taskKey}`);
      }

      const existingRuntime = stateManager.state.tasks[taskKey] || {};
      const normalizedStatus = normalizeTaskStatus(existingRuntime.status) || inferStatusFromIssue(taskIssue, config) || 'pending';
      const normalizedPrNumber = normalizePositiveInteger(existingRuntime.pr_number);

      stateManager.state.tasks[taskKey] = {
        task_key: taskKey,
        title: task.title,
        level: task.level,
        model: task.model,
        deps: Array.isArray(task.deps) ? task.deps.slice() : [],
        acceptance: task.acceptance,
        issue_number: taskIssueNumber,
        pr_number: normalizedPrNumber,
        status: normalizedStatus,
        created_at: existingRuntime.created_at || now,
        updated_at: now
      };

      createdIssues.push({ taskKey, issueNumber: taskIssueNumber });
    }

    stateManager.state.cursor_task_id = normalizeCursorTaskId(stateManager.state.cursor_task_id, stateManager.state.tasks);
    stateManager.state.revision += 1;
    stateManager.state.updated_at = now;
    await stateManager.save();

    core.setOutput('tasks_created', createdCount.toString());
    core.setOutput('tasks_total', createdIssues.length.toString());
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

function normalizeTaskStatus(status) {
  const normalized = String(status || '').trim().toLowerCase();
  if (!VALID_TASK_STATUSES.has(normalized)) {
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

function normalizeCursorTaskId(taskId, taskMap) {
  if (typeof taskId !== 'string' || taskId.trim() === '') {
    return null;
  }
  return taskMap[taskId] ? taskId : null;
}

function inferStatusFromIssue(issue, config) {
  if (!issue || !Array.isArray(issue.labels)) {
    return null;
  }

  const labels = new Set(issue.labels.map((label) => label.name));
  if (labels.has(config.labels.task.done)) {
    return 'done';
  }
  if (labels.has(config.labels.task.in_review)) {
    return 'in-review';
  }
  if (labels.has(config.labels.task.in_progress)) {
    return 'in-progress';
  }
  if (labels.has(config.labels.task.blocked)) {
    return 'blocked';
  }
  if (labels.has(config.labels.task.cancelled)) {
    return 'cancelled';
  }
  if (labels.has(config.labels.task.pending)) {
    return 'pending';
  }

  return null;
}

main();
