#!/usr/bin/env node

/**
 * Prompt Template Loader and Renderer
 * 
 * Loads prompt templates from files and renders them with variable substitution.
 * Supports strict validation to ensure all required variables are provided.
 * 
 * @module prompt-loader
 */

const fs = require('fs');
const path = require('path');

/**
 * Extract all placeholder variables from a template string
 * 
 * @param {string} template - Template content
 * @returns {string[]} - Array of variable names found in template
 * @private
 */
function extractPlaceholders(template) {
  const placeholderRegex = /\{\{(\w+)\}\}/g;
  const placeholders = new Set();
  let match;
  
  while ((match = placeholderRegex.exec(template)) !== null) {
    placeholders.add(match[1]);
  }
  
  return Array.from(placeholders);
}

/**
 * Substitute variables in template content
 * 
 * @param {string} template - Template content with {{variable}} placeholders
 * @param {Object} variables - Variables for substitution (camelCase keys)
 * @param {boolean} strict - If true, leave unmatched placeholders; if false, replace with empty string
 * @returns {string} - Rendered template
 * @private
 */
function substituteVariables(template, variables, strict) {
  let result = template;
  
  for (const [key, value] of Object.entries(variables)) {
    const pattern = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
    result = result.replace(pattern, String(value));
  }
  
  if (!strict) {
    result = result.replace(/\{\{\w+\}\}/g, '');
  }
  
  return result;
}

/**
 * Resolve template file path
 * 
 * Checks override directory first, then falls back to builtin templates.
 * 
 * @param {string} templateId - Template identifier (e.g., 'phase/spec')
 * @param {string|null} overrideDir - Custom template directory (optional)
 * @returns {string} - Resolved absolute path to template file
 * @throws {Error} - If template file not found in either location
 * @pri */
function resolveTemplatePath(templateId, overrideDir) {
  const templateFile = `${templateId}.md`;
  const searchedPaths = [];
  
  if (overrideDir) {
    const overridePath = path.resolve(overrideDir, templateFile);
    searchedPaths.push(overridePath);
    
    if (fs.existsSync(overridePath)) {
      return overridePath;
    }
  }
  
  const builtinPath = path.join(__dirname, '..', 'prompts', templateFile);
  searchedPaths.push(builtinPath);
  
  if (fs.existsSync(builtinPath)) {
    return builtinPath;
  }
  
  throw new Error(
    `Template not found: ${templateId}\n` +
    `Searched paths:\n${searchedPaths.map(p => `  - ${p}`).join('\n')}`
  );
}

/**
 * Load and render a prompt template with variable substitution
 * 
 * @param {string} templateId - Template identifier (e.g., 'phase/spec', 'phase/plan', 'dispatch/task')
 * @param {Object} variables - Variables for substitution (camelCase keys)
 * @param {Object} [options={}] - Rendering options
 * @param {boolean} [options.strict=true] - Throw on missing variables (default: true)
 * @param {string} [options.overrideDir] - Custom template directory (checked before builtin)
 * @returns {string} - Rendered prompt text
 * @throws {Error} - If template not found or variables missing (strict mode)
 * 
 * @example
 * // Load phase spec template with strict validation
 * const prompt = loadPrompt('phase/spec', {
 *   epicNumber: 123,
 *   specDir: 'docs/specs',
 *   baseBranch: 'main'
 * });
 * 
 * @example
 * // Load with custom override directory
 * const prompt = loadPrompt('phase/spec', variables, {
 *   overrideDir: '/custom/templates'
 * });
 * 
 * @example
 * // Non-strict mode (missing variables replaced with empty string)
 * const prompt = loadPrompt('phase/plan', variables, {
 *   strict: false
 * });
 */
function loadPrompt(templateId, variables = {}, options = {}) {
  const { strict = true, overrideDir = null } = options;
  
  if (!templateId || typeof templateId !== 'string') {
    throw new Error('templateId must be a non-empty string');
  }
  
  if (typeof variables !== 'object' || variables === null) {
    throw new Error('variables must be an object');
  }
  
  let templatePath;
  try {
    templatePath = resolveTemplatePath(templateId, overrideDir);
  } catch (error) {
    throw error;
  }
  
  let templateContent;
  try {
    templateContent = fs.readFileSync(templatePath, 'utf8');
  } catch (error) {
    throw new Error(
      `Failed to read template file: ${templatePath}\n` +
      `Error: ${error.message}`
    );
  }
  
  const placeholders = extractPlaceholders(templateContent);
  
  if (strict && placeholders.length > 0) {
    const providedKeys = Object.keys(variables);
    const missingVars = placeholders.filter(p => !providedKeys.includes(p));
    
    if (missingVars.length > 0) {
      throw new Error(
        `Missing prompt variables: ${missingVars.join(', ')}\n` +
        `Template: ${templateId}\n` +
        `Required: ${placeholders.join(', ')}\n` +
        `Provided: ${providedKeys.join(', ') || '(none)'}`
      );
    }
  }
  
  const rendered = substituteVariables(templateContent, variables, strict);
  
  return rendered;
}

module.exports = {
  loadPrompt,
  _internal: {
    extractPlaceholders,
    substituteVariables,
    resolveTemplatePath
  }
};
