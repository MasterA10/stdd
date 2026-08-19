import React, { useEffect, useState } from 'react';
import type { NodeData, Question } from '../types';
import { Plus, Trash2, X } from 'lucide-react';
import { ConfirmModal } from './ConfirmModal';
import { MentionTextarea } from '../utils';

interface QuestionsModalProps {
  node: NodeData;
  onClose: () => void;
  onUpdateQuestions: (nodeId: number, questions: Question[]) => void;
}

const emptyOptions = () => ['', ''];
const CUSTOM_ANSWER_VALUE = 'custom';
const isAnswered = (answer: Question['answer']) =>
  answer !== null && !(typeof answer === 'string' && answer.trim() === '');

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
  const [showDiscardDraftConfirm, setShowDiscardDraftConfirm] = useState(false);

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

  const hasUnsavedQuestionDraft = prompt.trim().length > 0 || options.some((option) => option.trim().length > 0);
  const requestClose = () => {
    if (hasUnsavedQuestionDraft) {
      setShowDiscardDraftConfirm(true);
      return;
    }
    onClose();
  };
  const discardDraftAndClose = () => {
    setShowDiscardDraftConfirm(false);
    setPrompt('');
    setQuestionType('open');
    setOptions(emptyOptions());
    onClose();
  };

  return (
    <>
      <div className="dialog-overlay">
        <dialog className="app-dialog questions-dialog" open onCancel={(event) => { event.preventDefault(); requestClose(); }}>
        <div className="dialog-content questions-modal-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">Looper · Perguntas e observações</p>
              <h2>{node.label}</h2>
            </div>
            <button className="close-btn" onClick={requestClose} type="button">
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
              <div key={question.id} className={`question-card question-editor-card ${isAnswered(question.answer) ? 'answered' : 'unanswered'}`}>
                <div className="question-card-header">
                  <div>
                    <span className="question-number">#{String(question.id).padStart(2, '0')}</span>
                    <strong>{question.type === 'open' ? 'Observação aberta' : question.type === 'boolean' ? 'Pergunta sim ou não' : 'Múltipla escolha'}</strong>
                  </div>
                  {!isAnswered(question.answer) && <span className="question-unanswered-badge"><span aria-hidden="true" />Sem resposta</span>}
                  <button
                    className="question-del-btn"
                    onClick={() => commit(questions.filter((item) => item.id !== question.id))}
                    title="Remover pergunta"
                    type="button"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
                <MentionTextarea
                  className="question-prompt-input"
                  value={question.prompt}
                  onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => updateQuestion(question.id, { prompt: event.target.value })}
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
                    <>
                      <select
                        className="question-answer-select"
                        value={typeof question.answer === 'string'
                          ? CUSTOM_ANSWER_VALUE
                          : question.answer === null || question.answer === undefined ? '' : String(question.answer)}
                        onChange={(event) => {
                          const value = event.target.value;
                          updateQuestion(question.id, {
                            answer: value === ''
                              ? null
                              : value === CUSTOM_ANSWER_VALUE
                                ? ''
                                : question.type === 'boolean'
                                  ? value === 'true'
                                  : Number(value)
                          });
                        }}
                      >
                        <option value="">Selecione uma resposta</option>
                        {question.type === 'boolean'
                          ? <><option value="true">Sim</option><option value="false">Não</option></>
                          : <>
                            {(question.options || []).map((option) => (
                              <option key={option.id} value={String(option.id)}>{option.label}</option>
                            ))}
                          </>}
                        <option value={CUSTOM_ANSWER_VALUE}>Outra resposta...</option>
                      </select>
                      {typeof question.answer === 'string' && (
                        <textarea
                          className="question-answer-textarea"
                          placeholder="Digite uma resposta personalizada..."
                          value={question.answer}
                          onChange={(event) => updateQuestion(question.id, { answer: event.target.value })}
                        />
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>

          <form className="editor-card question-create-card question-create-card-top" onSubmit={addQuestion}>
            <h3>Adicionar pergunta ou observação</h3>
            <MentionTextarea
              className="question-create-prompt"
              placeholder="Ex: Qual risco ainda precisa ser validado?"
              value={prompt}
              onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => setPrompt(event.target.value)}
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
      <ConfirmModal
        isOpen={showDiscardDraftConfirm}
        title="Descartar pergunta?"
        message="A pergunta e as respostas digitadas ainda não foram adicionadas. Deseja sair sem salvar?"
        confirmLabel="Sair sem salvar"
        cancelLabel="Continuar editando"
        isDanger
        onConfirm={discardDraftAndClose}
        onCancel={() => setShowDiscardDraftConfirm(false)}
      />
    </>
  );
};
