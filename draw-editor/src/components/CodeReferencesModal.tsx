import React from 'react';
import { Code2, FileCode2, X } from 'lucide-react';
import type { CodeReference, NodeData, TraceabilityFacts } from '../types';

interface CodeReferencesModalProps {
  node: NodeData;
  facts: TraceabilityFacts | null;
  onClose: () => void;
}

const asList = (value: unknown): string[] => (
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : []
);

export const CodeReferencesModal: React.FC<CodeReferencesModalProps> = ({ node, facts, onClose }) => {
  const references = (Array.isArray(node.code_refs) ? node.code_refs : []) as CodeReference[];
  const report = facts?.nodes?.[String(node.id)];
  const files = asList(report?.files);
  const declaredTestReferences = [
    ...(node.test_ref ? [node.test_ref] : []),
    ...(Array.isArray(node.test_refs) ? node.test_refs : [])
  ];
  const declaredTests = declaredTestReferences.flatMap((reference) => (
    typeof reference.file === 'string'
      ? asList(reference.symbols).map((symbol) => `${reference.file} · ${symbol}`)
      : []
  ));
  const tests = Array.from(new Set([...asList(report?.tests), ...declaredTests]));
  const unresolved = new Set(asList(report?.unresolved));

  return (
    <div className="dialog-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <dialog className="app-dialog code-references-dialog" open aria-labelledby="code-references-title">
        <div className="dialog-header">
          <div>
            <p className="eyebrow code-references-eyebrow"><Code2 size={13} /> Looper · Símbolos associados</p>
            <h2 id="code-references-title">{node.label}</h2>
            <p className="code-references-node-id">Nó #{node.id}</p>
          </div>
          <button className="close-btn" onClick={onClose} type="button" aria-label="Fechar símbolos associados">
            <X size={18} />
          </button>
        </div>

        <section className="code-reference-section">
          <div className="code-reference-section-title">
            <strong>Símbolos</strong>
            <span className="code-reference-total">{references.length}</span>
          </div>
          {references.length === 0 ? (
            <div className="code-reference-empty">Este nó ainda não possui símbolos associados.</div>
          ) : (
            <div className="code-reference-list">
              {references.map((reference, index) => {
                const symbol = typeof reference.symbol === 'string' ? reference.symbol : 'Símbolo sem nome';
                const file = typeof reference.file === 'string' && reference.file.trim().length > 0 ? reference.file.trim() : null;
                const resolvedReference = report?.references?.find((item) => item.symbol === symbol);
                const resolvedFile = typeof resolvedReference?.file === 'string' && resolvedReference.file.trim().length > 0 ? resolvedReference.file.trim() : null;
                const filePath = file || resolvedFile;
                const status = resolvedReference?.status || (unresolved.has(symbol) ? 'unresolved' : facts ? 'pending' : 'not-analyzed');
                return (
                  <article className="code-reference-card" key={`${symbol}-${index}`}>
                    <div className="code-reference-card-heading">
                      <Code2 size={15} />
                      <div className="code-reference-symbol-wrapper">
                        <code className="code-reference-symbol">{symbol}</code>
                        {filePath && (
                          <div className="code-reference-file-subtext">
                            <code>{filePath}</code>
                          </div>
                        )}
                      </div>
                      <span className={`code-reference-status ${status}`}>
                        {status === 'resolved' ? 'resolvido' : status === 'unresolved' ? 'não encontrado' : 'aguardando análise'}
                      </span>
                    </div>
                    {asList(reference.source_dependencies).length > 0 && (
                      <div className="code-reference-dependencies">
                        <span>Depende de</span>
                        {asList(reference.source_dependencies).map((dependency) => <code key={dependency}>{dependency}</code>)}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="code-reference-section">
          <div className="code-reference-section-title"><strong>Arquivos associados</strong><span className="code-reference-total">{files.length}</span></div>
          {files.length > 0 ? (
            <ul className="code-reference-files">
              {files.map((file) => <li key={file}><FileCode2 size={14} /><code>{file}</code></li>)}
            </ul>
          ) : (
            <div className="code-reference-empty">
              {facts
                ? 'A análise não resolveu arquivos para os símbolos deste nó.'
                : 'Os arquivos aparecerão aqui após o adapter estático gerar os fatos da análise.'}
            </div>
          )}
          {tests.length > 0 && (
            <div className="code-reference-tests"><strong>Testes relacionados</strong>{tests.map((test) => <code key={test}>{test}</code>)}</div>
          )}
        </section>
      </dialog>
    </div>
  );
};
