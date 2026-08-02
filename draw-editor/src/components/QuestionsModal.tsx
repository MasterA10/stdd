import React, { useEffect, useState } from 'react';
import type { NodeData, Question } from '../types';
import { Plus, Trash2, X } from 'lucide-react';

interface QuestionsModalProps {
  node: NodeData;
  onClose: () => void;
  onUpdateQuestions: (nodeId: number, questions: Question[]) => void;
}

const emptyOptions = () => ['', ''];

/** Permite criar, editar, responder e remover perguntas de um bloco. */
export const QuestionsModal: React.FC<QuestionsModalProps> = ({
  node,
  onClose,
  onUpdateQuestions
}) => {
  const [questions, setQuestions] = useState<Question[]>(node.questions || []);
  const [prompt, setPrompt] = useState('');
  const [questionType, setQuestionType] = useState<Question['type']>('open');
  const [options, setOptions] = useState<string[]>(emptyOptions());

  useEffect(() => {
    setQuestions(node.questions || []);
  }, [node.questions]);

  const commit = (nextQuestions: Question[]) => {
    setQuestions(nextQuestions);
    onUpdateQuestions(node.id, nextQuestions);
  };

  const updateQuestion = (questionId: number, patch: Partial<Question>) => {
    commit(questions.map((question) => (
      question.id === questionId ? { ...question, ...patch } : question
    )));
  };

  const addQuestion = (event: React.FormEvent) => {
    event.preventDefault();
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;

    const nextId = questions.length ? Math.max(...questions.map((question) => question.id)) + 1 : 1;
    const cleanOptions = options.map((option) => option.trim()).filter(Boolean)
      .map((label, index) => ({ id: index + 1, label }));
    if (questionType === 'choice' && cleanOptions.length < 2) return;

    const newQuestion: Question = {
      id: nextId,
      type: questionType,
      prompt: cleanPrompt,
      answer: null,
      ...(questionType === 'choice' ? { options: cleanOptions } : {})
    };
    commit([...questions, newQuestion]);
    setPrompt('');
    setQuestionType('open');
    setOptions(emptyOptions());
  };

  const updateOption = (index: number, value: string) => {
    setOptions(options.map((option, optionIndex) => optionIndex === index ? value : option));
  };

  return (
    <div className="dialog-overlay">
      <dialog className="app-dialog questions-dialog" open>
        <div className="dialog-content questions-modal-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">STDD · Perguntas e observações</p>
              <h2>{node.label}</h2>
            </div>
            <button className="close-btn" onClick={onClose} type="button">
              <X size={18} />
            </button>
          </div>

          <div className="question-list">
            {questions.length === 0 && (
              <div className="questions-empty-state">
                <span className="questions-empty-icon">?</span>
                <strong>Nenhuma pergunta ainda</strong>
                <p>Registre uma dúvida, decisão pendente ou observação para este bloco.</p>
              </div>
            )}
            {questions.map((question) => (
              <div key={question.id} className="question-card question-editor-card">
                <div className="question-card-header">
                  <div>
                    <span className="question-number">#{String(question.id).padStart(2, '0')}</span>
                    <strong>{question.type === 'open' ? 'Observação aberta' : question.type === 'boolean' ? 'Pergunta sim ou não' : 'Múltipla escolha'}</strong>
                  </div>
                  <button
                    className="question-del-btn"
                    onClick={() => commit(questions.filter((item) => item.id !== question.id))}
                    title="Remover pergunta"
                    type="button"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
                <input
                  className="question-prompt-input"
                  value={question.prompt}
                  onChange={(event) => updateQuestion(question.id, { prompt: event.target.value })}
                  aria-label={`Texto da pergunta ${question.id}`}
                />

                <div className="question-answer-field">
                  <span className="question-answer-label">Sua resposta</span>
                  {question.type === 'open' ? (
                    <textarea
                      className="question-answer-textarea"
                      placeholder="Escreva uma resposta, decisão ou observação..."
                      value={typeof question.answer === 'string' ? question.answer : ''}
                      onChange={(event) => updateQuestion(question.id, { answer: event.target.value })}
                    />
                  ) : (
                    <select
                      className="question-answer-select"
                      value={question.answer === null || question.answer === undefined ? '' : String(question.answer)}
                      onChange={(event) => {
                        const value = event.target.value;
                        updateQuestion(question.id, {
                          answer: value === ''
                            ? null
                            : question.type === 'boolean' ? value === 'true' : Number(value)
                        });
                      }}
                    >
                      <option value="">Selecione uma resposta</option>
                      {question.type === 'boolean'
                        ? <><option value="true">Sim</option><option value="false">Não</option></>
                        : (question.options || []).map((option) => (
                          <option key={option.id} value={String(option.id)}>{option.label}</option>
                        ))}
                    </select>
                  )}
                </div>
              </div>
            ))}
          </div>

          <form className="editor-card question-create-card" onSubmit={addQuestion}>
            <h3>Adicionar pergunta ou observação</h3>
            <textarea
              className="question-create-prompt"
              placeholder="Ex: Qual risco ainda precisa ser validado?"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              required
            />
            <div className="dialog-fields">
              <label>Tipo de resposta</label>
              <select className="question-type-select" value={questionType} onChange={(event) => setQuestionType(event.target.value as Question['type'])}>
                <option value="open">Texto / observação</option>
                <option value="boolean">Sim ou não</option>
                <option value="choice">Múltiplas opções</option>
              </select>
            </div>
            {questionType === 'choice' && (
              <div className="dialog-fields">
                <label>Opções</label>
                {options.map((option, index) => (
                  <div key={index} className="question-option-row">
                    <input
                      className="question-option-input"
                      placeholder={`Opção ${index + 1}`}
                      value={option}
                      onChange={(event) => updateOption(index, event.target.value)}
                    />
                    {options.length > 2 && (
                      <button className="close-btn" type="button" onClick={() => setOptions(options.filter((_, i) => i !== index))}>
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                ))}
                <button className="question-add-option-btn" type="button" onClick={() => setOptions([...options, ''])}>
                  <Plus size={14} /> Adicionar opção
                </button>
              </div>
            )}
            <button className="sidebar-submit-btn" type="submit">
              <Plus size={14} /> Adicionar pergunta
            </button>
          </form>

          <div className="dialog-actions">
            <button className="primary" onClick={onClose} type="button">Concluído</button>
          </div>
        </div>
      </dialog>
    </div>
  );
};
