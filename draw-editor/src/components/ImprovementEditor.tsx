import React from 'react';
import type { ImprovementSession } from '../types';

interface ImprovementEditorProps {
  session: ImprovementSession;
  onChange: (questionId: number, answer: string | boolean | number | null) => void;
}

const isAnswered = (answer: string | boolean | number | null) =>
  answer !== null && !(typeof answer === 'string' && answer.trim() === '');
const CUSTOM_ANSWER_VALUE = 'custom';

export const ImprovementEditor: React.FC<ImprovementEditorProps> = ({ session, onChange }) => {
  const answeredCount = session.questions.filter((question) => isAnswered(question.answer)).length;
  const readOnly = session.status === 'applied';

  return (
    <section className="improvement-editor" aria-label="Sessão de melhoria do Draw">
      <div className="improvement-editor-header">
        <div>
          <span className="eyebrow">Looper · Draw Improve</span>
          <h2>{session.title}</h2>
          <p>Draw associado: <code>{session.draw_id}</code>. As respostas são salvas separadamente do fluxo.</p>
        </div>
        <span className={`improvement-status ${session.status}`}>{session.status}</span>
      </div>
      <div className="improvement-progress" aria-label={`${answeredCount} de ${session.questions.length} perguntas respondidas`}>
        <strong>{answeredCount}/{session.questions.length}</strong> perguntas respondidas
      </div>
      <div className="improvement-question-list">
        {session.questions.map((question, index) => {
          const questionStateClass = isAnswered(question.answer) ? 'answered' : 'unanswered';
          return (
          <article className={`improvement-question-card ${questionStateClass}`} key={question.id}>
            <div className="improvement-question-card-heading">
              <label htmlFor={`improvement-question-${question.id}`}>Pergunta {index + 1}</label>
              {questionStateClass === 'unanswered' && <span className="question-unanswered-badge"><span aria-hidden="true" />Sem resposta</span>}
            </div>
            <p>{question.prompt}</p>
            {question.type === 'open' ? (
              <textarea
                id={`improvement-question-${question.id}`}
                disabled={readOnly}
                value={typeof question.answer === 'string' ? question.answer : ''}
                onChange={(event) => onChange(question.id, event.target.value)}
              />
            ) : (
              <>
                <select
                  id={`improvement-question-${question.id}`}
                  disabled={readOnly}
                  value={typeof question.answer === 'string'
                    ? CUSTOM_ANSWER_VALUE
                    : question.answer === null ? '' : String(question.answer)}
                  onChange={(event) => {
                    const value = event.target.value;
                    const answer = value === ''
                      ? null
                      : value === CUSTOM_ANSWER_VALUE
                        ? ''
                        : question.type === 'boolean'
                          ? value === 'true'
                          : Number(value);
                    onChange(question.id, answer);
                  }}
                >
                  <option value="">Ainda sem resposta</option>
                  {question.type === 'boolean' ? (
                    <>
                      <option value="true">Sim</option>
                      <option value="false">Não</option>
                    </>
                  ) : (question.options || []).map((option, optionIndex) => (
                    <option key={option.id} value={String(option.id)}>
                      {String.fromCharCode(65 + optionIndex)}. {option.label}
                    </option>
                  ))}
                  <option value={CUSTOM_ANSWER_VALUE}>Outra resposta...</option>
                </select>
                {typeof question.answer === 'string' && (
                  <textarea
                    className="question-answer-textarea"
                    disabled={readOnly}
                    value={question.answer}
                    placeholder="Digite uma resposta personalizada..."
                    onChange={(event) => onChange(question.id, event.target.value)}
                  />
                )}
              </>
            )}
          </article>
          );
        })}
      </div>
      {readOnly && <p className="improvement-readonly">Sessão aplicada. As respostas permanecem disponíveis para auditoria.</p>}
    </section>
  );
};
