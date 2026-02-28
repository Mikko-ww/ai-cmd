#!/usr/bin/env node

const core = require('@actions/core');
const { GitHubClient } = require('./lib/github-client');

const REQUIRED_LABELS = [
  {
    name: 'agent:requested',
    color: '0E8A16',
    description: 'Request issue created, awaiting spec generation'
  },
  {
    name: 'action-dispatch',
    color: '1D76DB',
    description: 'Issue created by workflow_dispatch intake'
  }
];

function normalizeText(value, fallback = '（未提供）') {
  const text = String(value || '').trim();
  return text.length > 0 ? text : fallback;
}

function parsePositiveInteger(value, fallback) {
  const parsed = Number.parseInt(String(value || '').trim(), 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function buildIssueTitle(rawTitle) {
  const title = String(rawTitle || '').trim();
  if (!title) {
    throw new Error('DISPATCH_TITLE is required');
  }

  return title.startsWith('[Request]') ? title : `[Request] ${title}`;
}

function buildSection(title, content) {
  return [
    `### ${title}`,
    '',
    content
  ].join('\n');
}

function buildIssueBody(inputs) {
  return [
    '## 欢迎使用GitHub自动智能体系统',
    '',
    '此 Issue 由 `manual-request-dispatch.yml` 工作流创建，用于兼容移动端无法使用 Issue 模板的场景。',
    '',
    buildSection('背景与目标', normalizeText(inputs.background)),
    '',
    buildSection('范围 - 包含', normalizeText(inputs.scopeIn)),
    '',
    buildSection('范围 - 不包含', normalizeText(inputs.scopeOut, '（无）')),
    '',
    buildSection('验收标准', normalizeText(inputs.acceptance)),
    '',
    buildSection('约束与禁止项', normalizeText(inputs.constraints, '（无）')),
    '',
    buildSection('计划任务数（期望）', String(inputs.planTaskTarget)),
    '',
    buildSection('最大任务条数', String(inputs.planTaskMax)),
    '',
    buildSection('补充信息', normalizeText(inputs.additional, '（无）')),
    '',
    buildSection('系统指纹（请勿修改）', '<!-- agent-request -->')
  ].join('\n');
}

function parseInputsFromEnv(env = process.env) {
  return {
    title: env.DISPATCH_TITLE,
    background: env.DISPATCH_BACKGROUND,
    scopeIn: env.DISPATCH_SCOPE_IN,
    scopeOut: env.DISPATCH_SCOPE_OUT,
    acceptance: env.DISPATCH_ACCEPTANCE,
    constraints: env.DISPATCH_CONSTRAINTS,
    planTaskTarget: parsePositiveInteger(env.DISPATCH_PLAN_TASK_TARGET, 5),
    planTaskMax: parsePositiveInteger(env.DISPATCH_PLAN_TASK_MAX, 8),
    additional: env.DISPATCH_ADDITIONAL
  };
}

async function ensureLabels(github) {
  const existing = await github.listLabels();
  const existingNames = new Set(existing.map((label) => label.name));

  for (const label of REQUIRED_LABELS) {
    if (!existingNames.has(label.name)) {
      await github.createLabel(label.name, label.color, label.description);
    }
  }
}

async function main() {
  try {
    const token = process.env.AGENT_GH_TOKEN || process.env.GITHUB_TOKEN;
    const [owner, repo] = String(process.env.GITHUB_REPOSITORY || '').split('/');

    if (!token || !owner || !repo) {
      core.setFailed('Missing required environment variables: AGENT_GH_TOKEN and GITHUB_REPOSITORY');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const inputs = parseInputsFromEnv();
    const issueTitle = buildIssueTitle(inputs.title);
    const issueBody = buildIssueBody(inputs);

    await ensureLabels(github);

    const issue = await github.createIssue(
      issueTitle,
      issueBody,
      ['agent:requested', 'action-dispatch']
    );

    core.setOutput('issue_number', String(issue.number));
    core.setOutput('issue_url', issue.html_url);
    core.info(`Created issue #${issue.number}: ${issue.html_url}`);
  } catch (error) {
    core.setFailed(`Failed to create dispatched agent request issue: ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  REQUIRED_LABELS,
  normalizeText,
  parsePositiveInteger,
  buildIssueTitle,
  buildIssueBody,
  parseInputsFromEnv,
  ensureLabels,
  main
};
