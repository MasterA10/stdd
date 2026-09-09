import React from 'react';
import { CheckCircle2, CircleHelp, ExternalLink, X } from 'lucide-react';
import type { Question } from '../types';

export interface GlobalQuestionEntry {
  drawId: string;
  drawTitle: string;
  nodeId: number;
  nodeLabel: string;
  question: Question;
}

interface GlobalQuestionsModalProps {
  entries: GlobalQuestionEntry[];
  loading: boolean;
  onClose: () => void;
  onOpenNode: (entry: GlobalQuestionEntry) => void;
}

const isAnswered = (answer: Question['answer']) =>
  answer !== null && !(typeof answer === 'string' && answer.trim() === '');

export const GlobalQuestionsModal: React.FC<GlobalQuestionsModalProps> = ({
  entries,
  loading,
  onClose,
  onOpenNode
}) => {
  const unansweredCount = entries.filter((entry) => !isAnswered(entry.question.answer)).length;

  return (
    <div className="dialog-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <dialog className="app-dialog questions-dialog global-questions-dialog" open aria-labelledby="global-questions-title">
        <div className="dialog-content questions-modal-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow"><CircleHelp size={13} /> Looper · Perguntas dos nós</p>
              <h2 id="global-questions-title">Perguntas do sistema</h2>
              <p className="global-questions-summary">
                {loading ? 'Varrendo todos os Draws...' : `${entries.length} pergunta(s) encontrada(s) · ${unansweredCount} em aberto`}
              </p>
            </div>
            <button className="close-btn" onClick={onClose} type="button" aria-label="Fechar perguntas do sistema">
              <X size={18} />
            </button>
          </div>

          {loading ? (
            <div className="questions-empty-state"><span className="questions-empty-icon">?</span><strong>Varrendo os nós</strong><p>Consultando as perguntas de todos os Draws.</p></div>
          ) : entries.length === 0 ? (
            <div className="questions-empty-state"><CheckCircle2 size={24} aria-hidden="true" /><strong>Nenhuma pergunta registrada</strong><p>Quando uma dúvida surgir, ela aparecerá aqui para acompanhamento centralizado.</p></div>
          ) : (
            <div className="global-question-list">
              {entries.map((entry) => {
                const answered = isAnswered(entry.question.answer);
                return (
                  <article className={`global-question-item ${answered ? 'answered' : 'unanswered'}`} key={`${entry.drawId}:${entry.nodeId}:${entry.question.id}`}>
                    <div className="global-question-status" aria-label={answered ? 'Respondida' : 'Sem resposta'}>
                      {answered ? <CheckCircle2 size={16} /> : <CircleHelp size={16} />}
                    </div>
                    <div className="global-question-copy">
                      <div className="global-question-meta"><strong>{entry.question.prompt}</strong><span>{answered ? 'Respondida' : 'Sem resposta'}</span></div>
                      <p>{entry.drawTitle} · {entry.nodeLabel} · pergunta #{entry.question.id}</p>
                    </div>
                    <button className="global-question-open" type="button" onClick={() => onOpenNode(entry)} title="Abrir nó de origem" aria-label={`Abrir ${entry.nodeLabel}`}>
                      <ExternalLink size={14} />
                    </button>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </dialog>
    </div>
  );
};
