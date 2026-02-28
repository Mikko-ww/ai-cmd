#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const core = require('@actions/core');

const DEFAULT_BASE_DIR = '.flowmind';
const BASED_PATH_KEYS = ['spec_dir', 'plan_yaml_dir', 'plan_md_dir'];

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function normalizeBaseDir(baseDir) {
  const normalized = typeof baseDir === 'string' ? baseDir.trim() : '';
  return normalized || DEFAULT_BASE_DIR;
}

function isAlreadyUnderBaseDir(baseDir, targetPath) {
  const normalizedBase = path.normalize(baseDir);
  const normalizedTarget = path.normalize(targetPath);

  return (
    normalizedTarget === normalizedBase ||
    normalizedTarget.startsWith(`${normalizedBase}${path.sep}`)
  );
}

function resolvePathWithBaseDir(baseDir, configuredPath) {
  if (typeof configuredPath !== 'string') {
    return configuredPath;
  }

  const normalizedPath = configuredPath.trim();
  if (!normalizedPath) {
    return configuredPath;
  }

  if (path.isAbsolute(normalizedPath)) {
    return normalizedPath;
  }

  if (!baseDir || baseDir === '.') {
    return normalizedPath;
  }

  if (isAlreadyUnderBaseDir(baseDir, normalizedPath)) {
    return normalizedPath;
  }

  return path.join(baseDir, normalizedPath);
}

function normalizeConfigPaths(config) {
  if (!isPlainObject(config)) {
    return config;
  }

  const flowmind = isPlainObject(config.flowmind) ? config.flowmind : {};
  const baseDir = normalizeBaseDir(flowmind.base_dir);
  const normalizedConfig = {
    ...config,
    flowmind: {
      ...flowmind,
      base_dir: baseDir
    }
  };

  if (!isPlainObject(config.paths)) {
    return normalizedConfig;
  }

  const normalizedPaths = {
    ...config.paths
  };

  for (const key of BASED_PATH_KEYS) {
    if (Object.prototype.hasOwnProperty.call(normalizedPaths, key)) {
      normalizedPaths[key] = resolvePathWithBaseDir(baseDir, normalizedPaths[key]);
    }
  }

  normalizedConfig.paths = normalizedPaths;
  return normalizedConfig;
}

function loadConfig(configPath = '.github/agent/config.yml') {
  try {
    const content = fs.readFileSync(configPath, 'utf8');
    const config = yaml.load(content);
    return normalizeConfigPaths(config);
  } catch (error) {
    core.error(`Failed to load config from ${configPath}: ${error.message}`);
    throw error;
  }
}

function getConfigValue(config, path) {
  const keys = path.split('.');
  let value = config;
  
  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key];
    } else {
      return undefined;
    }
  }
  
  return value;
}

module.exports = {
  loadConfig,
  getConfigValue,
  _internal: {
    normalizeBaseDir,
    resolvePathWithBaseDir,
    normalizeConfigPaths
  }
};
