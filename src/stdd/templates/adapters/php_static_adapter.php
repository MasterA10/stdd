<?php
// STDD_GENERATED_PHP_ADAPTER
// Adapter PHP determinístico baseado no tokenizer nativo do PHP.

$request = json_decode(stream_get_contents(STDIN), true);
$root = is_array($request) && isset($request['project_path']) ? realpath($request['project_path']) : false;
$result = [
    'contract_version' => '1', 'status' => 'passed',
    'capabilities' => [
        'symbols' => true, 'dependencies' => true, 'complexity' => true,
        'structural_metrics' => true, 'quality_findings' => true,
    ],
    'symbols' => [], 'dependencies' => [], 'complexity' => [], 'structural_metrics' => [],
    'quality_findings' => [], 'changes' => [], 'warnings' => [], 'errors' => [],
];

if (!$root || !is_dir($root)) {
    $result['status'] = 'blocked';
    $result['errors'][] = 'project_path inválido';
    echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
    exit(1);
}

$config = [];
$configPath = $root . DIRECTORY_SEPARATOR . '.stdd' . DIRECTORY_SEPARATOR . 'config.json';
if (is_file($configPath)) {
    $decoded = json_decode((string) file_get_contents($configPath), true);
    if (is_array($decoded)) $config = $decoded;
}
$quality = is_array($config['static_analysis']['quality'] ?? null) ? $config['static_analysis']['quality'] : [];
$limits = [
    'lines' => [
        'warning' => (int) ($quality['functions']['max_lines']['warning'] ?? 100),
        'blocking' => (int) ($quality['functions']['max_lines']['blocking'] ?? 150),
    ],
    'complexity' => [
        'warning' => (int) ($quality['functions']['max_complexity']['warning'] ?? 10),
        'blocking' => (int) ($quality['functions']['max_complexity']['blocking'] ?? 25),
    ],
    'parameters' => ['warning' => 5, 'blocking' => 9],
    'depth' => ['warning' => 4, 'blocking' => 6],
    'test_lines' => [
        'warning' => (int) ($quality['tests']['max_lines']['warning'] ?? 80),
        'blocking' => (int) ($quality['tests']['max_lines']['blocking'] ?? 160),
    ],
];

function significant_index(array $tokens, int $index): ?int {
    for ($i = $index; $i < count($tokens); $i++) {
        if (is_array($tokens[$i]) && in_array($tokens[$i][0], [T_WHITESPACE, T_COMMENT, T_DOC_COMMENT], true)) continue;
        return $i;
    }
    return null;
}

function matching_pairs(array $tokens): array {
    $pairs = [];
    $stack = [];
    foreach ($tokens as $index => $token) {
        $text = is_array($token) ? $token[1] : $token;
        if (in_array($text, ['(', '{', '['], true)) {
            $stack[] = [$text, $index];
            continue;
        }
        if (!in_array($text, [')', '}', ']'], true)) continue;
        $opening = ['}' => '{', ')' => '(', ']' => '['][$text];
        for ($j = count($stack) - 1; $j >= 0; $j--) {
            if ($stack[$j][0] !== $opening) continue;
            [, $start] = $stack[$j];
            $stack = array_slice($stack, 0, $j);
            $pairs[$start] = $index;
            $pairs[$index] = $start;
            break;
        }
    }
    return $pairs;
}

function namespace_for(array $tokens): string {
    $namespace = '';
    for ($i = 0; $i < count($tokens); $i++) {
        if (!is_array($tokens[$i]) || $tokens[$i][0] !== T_NAMESPACE) continue;
        for ($j = significant_index($tokens, $i + 1); $j !== null && $j < count($tokens); $j++) {
            $token = $tokens[$j];
            $text = is_array($token) ? $token[1] : $token;
            if ($text === ';' || $text === '{') break;
            if (is_array($token) && in_array($token[0], [T_STRING, T_NAME_QUALIFIED], true)) $namespace .= $text;
            elseif ($text === '\\') $namespace .= '\\';
        }
        break;
    }
    return trim($namespace, '\\');
}

function parameter_count(array $tokens, int $open, int $close): int {
    $hasContent = false;
    $depth = 0;
    $commas = 0;
    for ($i = $open + 1; $i < $close; $i++) {
        $token = $tokens[$i];
        $text = is_array($token) ? $token[1] : $token;
        if (is_array($token) && in_array($token[0], [T_WHITESPACE, T_COMMENT, T_DOC_COMMENT], true)) continue;
        $hasContent = true;
        if (in_array($text, ['(', '[', '{'], true)) $depth++;
        elseif (in_array($text, [')', ']', '}'], true)) $depth--;
        elseif ($text === ',' && $depth === 0) $commas++;
    }
    return $hasContent ? $commas + 1 : 0;
}

function is_test_file(string $relative): bool {
    $parts = array_map('strtolower', explode('/', $relative));
    return (bool) array_intersect($parts, ['test', 'tests', 'spec', 'specs', 'fixtures']);
}

function severity_for(int $value, array $limit): ?string {
    if ($value > $limit['blocking']) return 'blocking';
    if ($value > $limit['warning']) return 'warning';
    return null;
}

function add_quality_finding(array &$result, string $kind, string $severity, array $metric, int $limit, string $evidence): void {
    $result['quality_findings'][] = [
        'kind' => $kind, 'severity' => $severity, 'file' => $metric['file'],
        'symbol_id' => $metric['symbol_id'], 'value' => $metric['value'], 'limit' => $limit,
        'evidence' => $evidence, 'source' => 'php_token_get_all',
    ];
}

function analyze_php_file(string $code, string $relative, array &$result, array $limits): void {
    $tokens = token_get_all($code);
    $pairs = matching_pairs($tokens);
    $namespace = namespace_for($tokens);
    $classes = [];
    $functions = [];

    for ($i = 0; $i < count($tokens); $i++) {
        $token = $tokens[$i];
        if (!is_array($token)) continue;
        $id = $token[0];
        if (in_array($id, [T_CLASS, T_INTERFACE, T_TRAIT], true)) {
            $nameIndex = significant_index($tokens, $i + 1);
            if ($nameIndex === null || !is_array($tokens[$nameIndex]) || $tokens[$nameIndex][0] !== T_STRING) continue;
            $open = significant_index($tokens, $nameIndex + 1);
            // A declaração pode conter extends/implements entre o nome e a
            // abertura. Continue até a chave para indexar também classes de
            // testes como `final class ExampleTest extends TestCase`.
            while ($open !== null && $tokens[$open] !== '{') {
                $open = significant_index($tokens, $open + 1);
            }
            if ($open !== null && isset($pairs[$open])) {
                $classes[] = ['name' => $tokens[$nameIndex][1], 'line' => $tokens[$nameIndex][2], 'open' => $open, 'close' => $pairs[$open], 'qualified' => ($namespace ? $namespace . '\\' : '') . $tokens[$nameIndex][1]];
            }
        }
        if ($id === T_USE) {
            $targetIndex = significant_index($tokens, $i + 1);
            if ($targetIndex !== null && is_array($tokens[$targetIndex]) && in_array($tokens[$targetIndex][0], [T_STRING, T_NAME_QUALIFIED], true)) {
                $result['dependencies'][] = ['source' => $relative, 'target' => $tokens[$targetIndex][1], 'kind' => 'use', 'file' => $relative, 'source_tool' => 'php_token_get_all'];
            }
        }
        if ($id !== T_FUNCTION) continue;
        $nameIndex = significant_index($tokens, $i + 1);
        if ($nameIndex !== null && $tokens[$nameIndex] === '&') $nameIndex = significant_index($tokens, $nameIndex + 1);
        $name = ($nameIndex !== null && is_array($tokens[$nameIndex]) && $tokens[$nameIndex][0] === T_STRING) ? $tokens[$nameIndex][1] : '{closure}';
        $open = significant_index($tokens, ($nameIndex ?? $i) + 1);
        if ($open === null || $tokens[$open] !== '(' || !isset($pairs[$open])) continue;
        $close = $pairs[$open];
        $body = significant_index($tokens, $close + 1);
        if ($body === null || $tokens[$body] !== '{' || !isset($pairs[$body])) continue;
        $class = null;
        foreach ($classes as $candidate) {
            if ($body > $candidate['open'] && $body < $candidate['close'] && ($class === null || $candidate['open'] > $class['open'])) $class = $candidate;
        }
        $qualified = ($class ? $class['qualified'] . '::' : ($namespace ? $namespace . '\\' : '')) . $name;
        $symbolId = $relative . ':' . $token[2] . ':' . $qualified;
        $functions[] = ['name' => $name, 'qualified' => $qualified, 'symbol_id' => $symbolId, 'start' => $token[2], 'open' => $body, 'close' => $pairs[$body], 'parameters' => parameter_count($tokens, $open, $close), 'file' => $relative];
    }

    foreach ($classes as $class) {
        $result['symbols'][] = ['symbol_id' => $relative . ':' . $class['qualified'], 'qualified_name' => $class['qualified'], 'kind' => 'class', 'file' => $relative, 'line' => $class['line'], 'source' => 'php_token_get_all'];
    }
    foreach ($functions as $function) {
        $result['symbols'][] = ['symbol_id' => $function['symbol_id'], 'qualified_name' => $function['qualified'], 'kind' => $function['name'] === '{closure}' ? 'closure' : 'function', 'file' => $relative, 'line' => $function['start'], 'source' => 'php_token_get_all'];
        $complexity = 1;
        $depth = 0;
        $maxDepth = 0;
        $endLine = $function['start'];
        for ($i = $function['open'] + 1; $i < $function['close']; $i++) {
            $token = $tokens[$i];
            $id = is_array($token) ? $token[0] : null;
            $text = is_array($token) ? $token[1] : $token;
            if (is_array($token)) $endLine = $token[2];
            if (in_array($text, ['{', '(', '['], true)) {
                if ($text === '{') { $depth++; $maxDepth = max($maxDepth, $depth); }
            } elseif ($text === '}') {
                $depth = max(0, $depth - 1);
            }
            if (in_array($id, [T_IF, T_ELSEIF, T_FOR, T_FOREACH, T_WHILE, T_CASE, T_CATCH, T_BOOLEAN_AND, T_BOOLEAN_OR], true) || in_array($text, ['&&', '||'], true) || ($text === '?' && ($i + 1 >= count($tokens) || $tokens[$i + 1] !== '?'))) $complexity++;
        }
        $lines = $endLine - $function['start'] + 1;
        $lineKind = is_test_file($relative) ? 'long_test' : 'long_function';
        $lineLimit = is_test_file($relative) ? $limits['test_lines'] : $limits['lines'];
        $metrics = [['metric' => 'lines', 'value' => $lines, 'limit' => $lineLimit, 'kind' => $lineKind], ['metric' => 'cyclomatic', 'value' => $complexity, 'limit' => $limits['complexity'], 'kind' => 'high_complexity'], ['metric' => 'parameters', 'value' => $function['parameters'], 'limit' => $limits['parameters'], 'kind' => 'too_many_parameters'], ['metric' => 'depth', 'value' => $maxDepth, 'limit' => $limits['depth'], 'kind' => 'deep_nesting']];
        foreach ($metrics as $metric) {
            $result['complexity'][] = ['symbol_id' => $function['symbol_id'], 'qualified_name' => $function['qualified'], 'file' => $relative, 'lines' => $lines, 'parameters' => $function['parameters'], 'cyclomatic' => $complexity, 'max_depth' => $maxDepth, 'metric' => $metric['metric'], 'value' => $metric['value'], 'source' => 'php_token_get_all'];
            $severity = severity_for($metric['value'], $metric['limit']);
            if ($severity !== null) add_quality_finding($result, $metric['kind'], $severity, ['file' => $relative, 'symbol_id' => $function['symbol_id'], 'value' => $metric['value']], $metric['limit'][$severity === 'blocking' ? 'blocking' : 'warning'], $metric['metric'] . ' acima do limite configurado');
        }
    }
    $result['structural_metrics'][] = ['file' => $relative, 'lines' => substr_count($code, "\n") + 1, 'classes' => count($classes), 'functions' => count($functions), 'source' => 'php_token_get_all'];
}

$files = [];
$iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS));
foreach ($iterator as $file) {
    if (!$file->isFile() || strtolower($file->getExtension()) !== 'php') continue;
    $relative = str_replace(DIRECTORY_SEPARATOR, '/', substr($file->getPathname(), strlen($root) + 1));
    if (preg_match('~(^|/)(\.git|\.stdd|vendor|node_modules|__pycache__)(/|$)~', $relative) || str_starts_with(basename($relative), '._')) continue;
    $files[] = [$file->getPathname(), $relative];
}
usort($files, fn($a, $b) => $a[1] <=> $b[1]);
foreach ($files as [$filename, $relative]) {
    $code = file_get_contents($filename);
    if ($code !== false) analyze_php_file($code, $relative, $result, $limits);
}

usort($result['symbols'], fn($a, $b) => [$a['file'], $a['line'], $a['qualified_name']] <=> [$b['file'], $b['line'], $b['qualified_name']]);
usort($result['complexity'], fn($a, $b) => [$a['file'], $a['symbol_id'], $a['metric']] <=> [$b['file'], $b['symbol_id'], $b['metric']]);
usort($result['quality_findings'], fn($a, $b) => [$a['file'], $a['symbol_id'], $a['kind']] <=> [$b['file'], $b['symbol_id'], $b['kind']]);
usort($result['structural_metrics'], fn($a, $b) => $a['file'] <=> $b['file']);
echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
