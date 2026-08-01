import React from 'react';
import type { NodeData } from '../types';
import { X } from 'lucide-react';

interface QuestionsModalProps {
  node: NodeData;
  onClose: () => void;
  onUpdateAnswer: (nodeId: number, questionId: number, answer: string | boolean | number | null) => void;
}

export const QuestionsModal: React.FC<QuestionsModalProps> = ({
  node,
  onClose,
  onUpdateAnswer
}) => {
  return (
    <div className="dialog-overlay">
      <dialog className="app-dialog" open>
        <div className="dialog-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">STDD · Questões do Bloco</p>
              <h2>Perguntas: {node.label}</h2>
            </div>
            <button className="close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          <div className="question-list">
            {(node.questions || []).map((q) => {
              const handleOpenChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
                onUpdateAnswer(node.id, q.id, e.target.value);
              };

              const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
                const val = e.target.value;
                const answer =
                  val === ''
                    ? null
                    : q.type === 'boolean'
                    ? val === 'true'
                    : Number(val);
                onUpdateAnswer(node.id, q.id, answer);
              };

              return (
                <div key={q.id} className="question-card">
                  <label>Pergunta #{q.id}</label>
                  <p>{q.prompt}</p>

                  {q.type === 'open' ? (
                    <textarea
                      placeholder="Sua resposta..."
                      defaultValue={String(q.answer || '')}
                      onChange={handleOpenChange}
                    />
                  ) : (
                    <select
                      defaultValue={
                        q.answer === null || q.answer === undefined
                          ? ''
                          : String(q.answer)
                      }
                      onChange={handleSelectChange}
                    >
                      <option value="">Ainda sem resposta</option>
                      {q.type === 'boolean' ? (
                        <>
                          <option value="true">Sim</option>
                          <option value="false">Não</option>
                        </>
                      ) : (
                        (q.options || []).map((opt) => (
                          <option key={opt.id} value={String(opt.id)}>
                            {opt.label}
                          </option>
                        ))
                      )}
                    </select>
                  )}
                </div>
              );
            })}
          </div>

          <div className="dialog-actions">
            <button className="primary" onClick={onClose}>
              Concluído
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
};
