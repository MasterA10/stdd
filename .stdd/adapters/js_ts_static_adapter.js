#!/usr/bin/env node
/* STDD JavaScript/TypeScript adapter. Uses the local TypeScript compiler API. */
const fs = require('fs');
const path = require('path');

const IGNORED = new Set(['.git', '.stdd', 'node_modules', 'vendor', 'dist', 'build', 'coverage', 'draw_assets']);
const EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']);
const result = {
  contract_version: '1', status: 'passed',
  capabilities: { symbols: true, dependencies: true, complexity: true, structural_metrics: true, changes: false, frontend: false },
  symbols: [], dependencies: [], technologies: [], external_logic: [], complexity: [], structural_metrics: [], quality_findings: [], changes: [], warnings: [], errors: []
};

function fail(message, code = 0) {
  result.status = 'blocked'; result.errors.push(message);
  process.stdout.write(JSON.stringify(result) + '\n'); process.exit(code);
}

let request;
try { request = JSON.parse(fs.readFileSync(0, 'utf8')); } catch (_) { fail('javascript_adapter_invalid_request'); }
const root = request && request.project_path ? path.resolve(request.project_path) : null;
if (!root || !fs.existsSync(root)) fail('project_path inválido', 1);

function findTypeScript() {
  const candidates = [root, ...walkDirs(root, 3)].map(dir => path.join(dir, 'node_modules', 'typescript'));
  for (const candidate of candidates) {
    try { return require(path.join(candidate, 'lib', 'typescript.js')); } catch (_) {}
  }
  try { return require('typescript'); } catch (_) { return null; }
}
function walkDirs(dir, depth) {
  if (depth <= 0) return [];
  let entries = [];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (_) { return []; }
  const dirs = [];
  for (const entry of entries) {
    if (entry.isDirectory() && !IGNORED.has(entry.name)) {
      const child = path.join(dir, entry.name); dirs.push(child, ...walkDirs(child, depth - 1));
    }
  }
  return dirs;
}
const ts = findTypeScript();
if (!ts) { result.status = 'unavailable'; result.capabilities = { symbols: false, dependencies: false, complexity: false, structural_metrics: false, changes: false, frontend: false }; result.warnings.push('typescript_parser_unavailable'); process.stdout.write(JSON.stringify(result) + '\n'); process.exit(0); }

function files(dir) {
  const found = [];
  function visit(current) {
    let entries = []; try { entries = fs.readdirSync(current, { withFileTypes: true }); } catch (_) { return; }
    for (const entry of entries) {
      if (IGNORED.has(entry.name)) continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) visit(full);
      else if (EXTENSIONS.has(path.extname(entry.name).toLowerCase())) found.push(full);
    }
  }
  visit(dir); return found.sort();
}
function rel(file) { return path.relative(root, file).split(path.sep).join('/'); }
function sourceFor(file) { return fs.readFileSync(file, 'utf8'); }
function lineOf(source, pos) { return source.slice(0, pos).split('\n').length; }
function endLine(source, pos) { return source.slice(0, pos).split('\n').length; }
function id(file, qualified, kind) { return `${rel(file)}:${kind}:${qualified}`; }
function isTest(file) { return /(^|\/)(test|tests|spec|specs|fixtures)(\/|$)|(^|\/)[^/]*(test|spec)[^/]*\./i.test(rel(file)); }
function limits() {
  try {
    const config = JSON.parse(fs.readFileSync(path.join(root, '.stdd', 'config.json'), 'utf8'));
    const q = config.static_analysis?.quality || {};
    return {
      lines: q.functions?.max_lines || { warning: 100, blocking: 150 },
      complexity: q.functions?.max_complexity || { warning: 10, blocking: 25 },
      tests: q.tests?.max_lines || { warning: 80, blocking: 160 },
      parameters: { warning: 5, blocking: 9 }, depth: { warning: 4, blocking: 6 }
    };
  } catch (_) { return { lines:{warning:100,blocking:150}, complexity:{warning:10,blocking:25}, tests:{warning:80,blocking:160}, parameters:{warning:5,blocking:9}, depth:{warning:4,blocking:6} }; }
}
function finding(kind, value, limit, file, symbolId, evidence) {
  const severity = value > limit.blocking ? 'blocking' : value > limit.warning ? 'warning' : null;
  if (severity) result.quality_findings.push({ kind, severity, file: rel(file), symbol_id: symbolId, value, limit: limit[severity], evidence, source: 'typescript_compiler_api' });
}
function complexity(node) {
  let value = 1, maxDepth = 0;
  function visit(n, depth) {
    if (n !== node && (ts.isIfStatement(n) || ts.isForStatement(n) || ts.isForInStatement(n) || ts.isForOfStatement(n) || ts.isWhileStatement(n) || ts.isDoStatement(n) || ts.isCaseClause(n) || ts.isCatchClause(n) || ts.isConditionalExpression(n))) value++;
    if (ts.isBinaryExpression(n) && (n.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken || n.operatorToken.kind === ts.SyntaxKind.BarBarToken || n.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken)) value++;
    const next = ts.isBlock(n) || ts.isModuleBlock(n) ? depth + 1 : depth; maxDepth = Math.max(maxDepth, next);
    ts.forEachChild(n, child => visit(child, next));
  }
  visit(node, 0); return { value, maxDepth };
}
function declarationName(node) { return node.name && node.name.getText ? node.name.getText() : '<anonymous>'; }
function visitFile(file) {
  const source = sourceFor(file); const scriptKind = file.endsWith('.tsx') ? ts.ScriptKind.TSX : file.endsWith('.jsx') ? ts.ScriptKind.JSX : file.endsWith('.ts') ? ts.ScriptKind.TS : ts.ScriptKind.JS;
  const sf = ts.createSourceFile(rel(file), source, ts.ScriptTarget.Latest, true, scriptKind);
  const symbols = new Map(); const imports = [];
  function walk(node, parents = []) {
    let currentParents = parents;
    if (ts.isImportDeclaration(node) && node.moduleSpecifier) imports.push(node.moduleSpecifier.text);
    if (ts.isClassDeclaration(node) && node.name) {
      const qualified = [...parents, declarationName(node)].join('.'); const symbolId = id(file, qualified, 'class');
      symbols.set(symbolId, { symbol_id:symbolId, qualified_name:qualified, kind:'class', name:declarationName(node), file:rel(file), line:lineOf(source,node.getStart(sf)), end_line:endLine(source,node.end), source:'typescript_compiler_api', _node:node }); currentParents = [...parents, declarationName(node)];
    } else if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) || ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
      const name = declarationName(node); const qualified = [...parents, name].join('.'); const kind = ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) ? 'method' : 'function'; const symbolId = id(file, qualified, kind);
      symbols.set(symbolId, { symbol_id:symbolId, qualified_name:qualified, kind, name, signature:node.getText(sf).slice(0, Math.max(0, node.getText(sf).indexOf('{')) || node.getText(sf).length).split('\n')[0].trim(), file:rel(file), line:lineOf(source,node.getStart(sf)), end_line:endLine(source,node.end), source:'typescript_compiler_api', _node:node });
    }
    ts.forEachChild(node, child => walk(child, currentParents));
  }
  walk(sf); return { file, source, sf, symbols, imports };
}
const parsed = files(root).map(visitFile); const index = new Map();
for (const item of parsed) for (const symbol of item.symbols.values()) { index.set(symbol.qualified_name, symbol); result.symbols.push({ ...symbol, _node:undefined }); }
for (const item of parsed) {
  const modules = new Set();
  for (const module of item.imports) { modules.add(module); result.dependencies.push({ source:rel(item.file), target:module, kind:'import', file:rel(item.file), source_tool:'typescript_compiler_api' }); }
  for (const symbol of item.symbols.values()) {
    if (!symbol._node || (!symbol._node.body && !symbol._node.initializer)) continue;
    const metrics = complexity(symbol._node); const lines = symbol.end_line - symbol.line + 1; const params = symbol._node.parameters ? symbol._node.parameters.length : 0;
    result.complexity.push({ symbol_id:symbol.symbol_id, qualified_name:symbol.qualified_name, file:rel(item.file), line:symbol.line, lines, parameters:params, cyclomatic:metrics.value, max_depth:metrics.maxDepth, source:'typescript_compiler_api' });
    const lim = limits(); const lineLimit = isTest(item.file) ? lim.tests : lim.lines; finding(isTest(item.file)?'long_test':'long_function',lines,lineLimit,item.file,symbol.symbol_id,`${lines} linhas em ${symbol.qualified_name}`); finding('high_complexity',metrics.value,lim.complexity,item.file,symbol.symbol_id,`complexidade ciclomática ${metrics.value}`); finding('too_many_parameters',params,lim.parameters,item.file,symbol.symbol_id,`${params} parâmetros`); finding('deep_nesting',metrics.maxDepth,lim.depth,item.file,symbol.symbol_id,`profundidade máxima ${metrics.maxDepth}`);
    function calls(node) { if (ts.isCallExpression(node) || ts.isNewExpression(node)) { const target = node.expression?.getText(item.sf); if (target) result.dependencies.push({ source:symbol.qualified_name, target, kind:'calls', file:rel(item.file), source_file:rel(item.file), source_tool:'typescript_compiler_api', resolution:'unresolved' }); } ts.forEachChild(node,calls); }
    calls(symbol._node);
  }
  result.structural_metrics.push({ file:rel(item.file), lines:item.source.split('\n').length, classes:[...item.symbols.values()].filter(s=>s.kind==='class').length, functions:[...item.symbols.values()].filter(s=>s.kind==='function'||s.kind==='method').length, imports:modules.size, source:'typescript_compiler_api' });
}
const seen = new Set();
for (const key of ['symbols','dependencies','complexity','structural_metrics','quality_findings']) { result[key] = result[key].filter(item => { const k=JSON.stringify(item); if (seen.has(`${key}:${k}`)) return false; seen.add(`${key}:${k}`); return true; }).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))); }
if (parsed.some(item => /\.tsx?$/.test(item.file))) { result.technologies.push({ name:'typescript', kind:'language', evidence:[{file:'package.json',source:'manifest'}] }); result.warnings.push('frontend_rules_unavailable: JSX/TSX symbols are collected, but route/asset/interaction checks require a framework-specific resolver'); }
process.stdout.write(JSON.stringify(result) + '\n');
