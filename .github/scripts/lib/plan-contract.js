#!/usr/bin/env node

const fs = require('fs');
const yaml = require('js-yaml');
const schema = require('./plan-schema.v1.json');

const REQUIRED_TASK_FIELDS = schema.properties.tasks.items.required;
const TASK_ID_PATTERN = new RegExp(schema.properties.tasks.items.properties.id.pattern);
const LEVEL_ENUM = new Set(schema.properties.tasks.items.properties.level.enum);
const KEY_PATTERN = new RegExp(schema['x-key-pattern']);
const FORBIDDEN_KEYS = new Set(
  (schema['x-forbidden-keys'] || []).map((key) => String(key).toLowerCase())
);

class PlanValidationError extends Error {
  constructor(code, message, path = '/', hint = '', details = {}) {
    super(message);
    this.name = 'PlanValidationError';
    this.code = code;
    this.path = path;
    this.hint = hint;
    this.details = details;
  }
}

function escapeJsonPointer(value) {
  return String(value).replace(/~/g, '~0').replace(/\//g, '~1');
}

function withPath(base, key) {
  return `${base}/${escapeJsonPointer(key)}`;
}

function raise(code, message, path = '/', hint = '', details = {}) {
  throw new PlanValidationError(code, message, path, hint, details);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

function validateKeyName(key, path) {
  const normalized = String(key).toLowerCase();
  if (FORBIDDEN_KEYS.has(normalized)) {
    raise(
      'PLAN_FORBIDDEN_ALIAS_KEY',
      `Forbidden key: ${key}`,
      path,
      'Use canonical keys defined in plan contract v1'
    );
  }

  if (!KEY_PATTERN.test(String(key))) {
    raise(
      'PLAN_FORBIDDEN_NON_MACHINE_KEY',
      `Invalid key format: ${key}`,
      path,
      'Use machine keys matching ^[a-z][a-z0-9_]*$'
    );
  }
}

function validateTaskShape(task, index) {
  const taskPath = `/tasks/${index}`;

  if (!isPlainObject(task)) {
    raise('PLAN_TASK_OBJECT_INVALID', 'Task item must be an object', taskPath);
  }

  for (const key of Object.keys(task)) {
    validateKeyName(key, withPath(taskPath, key));
  }

  for (const field of REQUIRED_TASK_FIELDS) {
    if (!hasOwn(task, field)) {
      raise(
        'PLAN_REQUIRED_FIELD_MISSING',
        `Missing required task field: ${field}`,
        taskPath,
        'Ensure all required fields are present: id,title,level,deps,acceptance'
      );
    }
  }

  if (typeof task.id !== 'string' || !TASK_ID_PATTERN.test(task.id)) {
    raise(
      'PLAN_TASK_ID_INVALID',
      `Invalid task id: ${task.id}`,
      withPath(taskPath, 'id'),
      'Task id must match ^task-[a-z0-9][a-z0-9-]{0,62}$'
    );
  }

  if (typeof task.title !== 'string' || task.title.trim() === '') {
    raise(
      'PLAN_FIELD_TYPE_INVALID',
      'title must be a non-empty string',
      withPath(taskPath, 'title')
    );
  }

  if (typeof task.level !== 'string' || !LEVEL_ENUM.has(task.level)) {
    raise(
      'PLAN_LEVEL_INVALID',
      `Invalid task level: ${task.level}`,
      withPath(taskPath, 'level'),
      'Allowed values: l1, l2, l3'
    );
  }

  if (!Array.isArray(task.deps)) {
    raise(
      'PLAN_DEPS_INVALID',
      'deps must be an array of task ids',
      withPath(taskPath, 'deps'),
      'Use [] when no dependency exists'
    );
  }

  for (let depIndex = 0; depIndex < task.deps.length; depIndex += 1) {
    const dep = task.deps[depIndex];
    const depPath = `${withPath(taskPath, 'deps')}/${depIndex}`;
    if (typeof dep !== 'string' || !TASK_ID_PATTERN.test(dep)) {
      raise(
        'PLAN_DEPS_INVALID',
        `Invalid dependency id: ${dep}`,
        depPath,
        'Dependency ids must match task id format (task-<slug>)'
      );
    }
  }

  if (typeof task.acceptance !== 'string' || task.acceptance.trim() === '') {
    raise(
      'PLAN_FIELD_TYPE_INVALID',
      'acceptance must be a non-empty string',
      withPath(taskPath, 'acceptance')
    );
  }

  if (hasOwn(task, 'notes') && typeof task.notes !== 'string') {
    raise(
      'PLAN_FIELD_TYPE_INVALID',
      'notes must be a string when provided',
      withPath(taskPath, 'notes')
    );
  }

  if (hasOwn(task, 'model')) {
    if (typeof task.model !== 'string' || task.model.trim() === '') {
      raise(
        'PLAN_FIELD_TYPE_INVALID',
        'model must be a non-empty string when provided',
        withPath(taskPath, 'model')
      );
    }
  }
}

function ensureNoDuplicateTaskIds(tasks) {
  const seen = new Map();
  for (let index = 0; index < tasks.length; index += 1) {
    const id = tasks[index].id;
    if (seen.has(id)) {
      raise(
        'PLAN_TASK_ID_DUPLICATE',
        `Duplicate task id: ${id}`,
        `/tasks/${index}/id`,
        'Each task id must be unique'
      );
    }
    seen.set(id, index);
  }
}

function ensureDependenciesExist(tasks) {
  const taskIds = new Set(tasks.map((task) => task.id));

  for (let taskIndex = 0; taskIndex < tasks.length; taskIndex += 1) {
    const task = tasks[taskIndex];
    for (let depIndex = 0; depIndex < task.deps.length; depIndex += 1) {
      const dep = task.deps[depIndex];
      const depPath = `/tasks/${taskIndex}/deps/${depIndex}`;

      if (dep === task.id) {
        raise(
          'PLAN_DEPS_SELF_REFERENCE',
          `Task ${task.id} cannot depend on itself`,
          depPath
        );
      }

      if (!taskIds.has(dep)) {
        raise(
          'PLAN_DEPS_REF_NOT_FOUND',
          `Dependency not found: ${dep}`,
          depPath,
          'Every dependency must reference an existing task id'
        );
      }
    }
  }
}

function ensureNoDependencyCycles(tasks) {
  const graph = new Map(tasks.map((task) => [task.id, task.deps]));
  const visiting = new Set();
  const visited = new Set();
  const stack = [];

  function dfs(taskId) {
    if (visiting.has(taskId)) {
      const cycleStart = stack.indexOf(taskId);
      const cycle = stack.slice(cycleStart).concat(taskId);
      raise(
        'PLAN_DEPS_CYCLE',
        `Dependency cycle detected: ${cycle.join(' -> ')}`,
        '/tasks',
        'Remove circular dependencies from deps'
      );
    }

    if (visited.has(taskId)) {
      return;
    }

    visiting.add(taskId);
    stack.push(taskId);

    const deps = graph.get(taskId) || [];
    for (const dep of deps) {
      dfs(dep);
    }

    stack.pop();
    visiting.delete(taskId);
    visited.add(taskId);
  }

  for (const taskId of graph.keys()) {
    dfs(taskId);
  }
}

function validatePlanObject(plan, options = {}) {
  const mode = options.mode || 'strict';
  if (mode !== 'strict') {
    raise('PLAN_MODE_UNSUPPORTED', `Unsupported mode: ${mode}`, '/', 'Use mode: strict');
  }

  if (!isPlainObject(plan)) {
    raise('PLAN_SCHEMA_INVALID', 'Plan root must be an object', '/');
  }

  for (const key of Object.keys(plan)) {
    validateKeyName(key, withPath('', key));
  }

  if (!hasOwn(plan, 'tasks')) {
    raise('PLAN_REQUIRED_FIELD_MISSING', 'Missing required root field: tasks', '/');
  }

  if (!Array.isArray(plan.tasks) || plan.tasks.length === 0) {
    raise('PLAN_SCHEMA_INVALID', 'tasks must be a non-empty array', '/tasks');
  }

  for (let index = 0; index < plan.tasks.length; index += 1) {
    validateTaskShape(plan.tasks[index], index);
  }

  ensureNoDuplicateTaskIds(plan.tasks);
  ensureDependenciesExist(plan.tasks);
  ensureNoDependencyCycles(plan.tasks);

  return plan;
}

function loadPlanOrFail(planPath, options = {}) {
  if (!planPath || typeof planPath !== 'string') {
    raise('PLAN_FILE_INVALID', 'planPath must be a non-empty string', '/');
  }

  if (!fs.existsSync(planPath)) {
    raise('PLAN_FILE_NOT_FOUND', `Plan file not found: ${planPath}`, '/');
  }

  let content;
  try {
    content = fs.readFileSync(planPath, 'utf8');
  } catch (error) {
    raise('PLAN_FILE_READ_ERROR', `Failed to read plan file: ${error.message}`, '/');
  }

  let parsed;
  try {
    parsed = yaml.load(content);
  } catch (error) {
    raise('PLAN_PARSE_ERROR', `Failed to parse YAML: ${error.message}`, '/', 'Fix YAML syntax and try again');
  }

  return validatePlanObject(parsed, options);
}

function tryLoadPlan(planPath, options = {}) {
  try {
    return {
      ok: true,
      plan: loadPlanOrFail(planPath, options)
    };
  } catch (error) {
    if (error instanceof PlanValidationError) {
      return {
        ok: false,
        error
      };
    }
    throw error;
  }
}

function formatValidationError(error) {
  if (!(error instanceof PlanValidationError)) {
    return {
      ok: false,
      code: 'PLAN_UNKNOWN_ERROR',
      path: '/',
      message: error && error.message ? error.message : 'Unknown validation error',
      hint: ''
    };
  }

  return {
    ok: false,
    code: error.code,
    path: error.path,
    message: error.message,
    hint: error.hint,
    details: error.details
  };
}

module.exports = {
  PlanValidationError,
  loadPlanOrFail,
  tryLoadPlan,
  validatePlanObject,
  formatValidationError,
  constants: {
    requiredTaskFields: REQUIRED_TASK_FIELDS,
    allowedLevels: Array.from(LEVEL_ENUM),
    forbiddenKeys: Array.from(FORBIDDEN_KEYS)
  }
};
