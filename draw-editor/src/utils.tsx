import { useRef, useEffect } from 'react';

export function renderWithMentions(text: string) {
  if (!text) return text;
  const regex = /(@stdd|@developer|@obs)/gi;
  const parts = text.split(regex);
  return parts.map((part, i) => {
    if (part.match(regex)) {
      return <span key={i} className="mention-tag">{part}</span>;
    }
    return part;
  });
}

export const MentionTextarea = ({ value, onChange, placeholder, className, rows = 2, 'aria-label': ariaLabel, required }: any) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  useEffect(() => {
    handleInput();
  }, [value]);

  return (
    <div className={`mention-textarea-wrapper ${className}-wrapper`} style={{ position: 'relative' }}>
      <div 
        className={`${className}-display`}
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          whiteSpace: 'pre-wrap',
          wordWrap: 'break-word',
          overflowWrap: 'anywhere',
          color: value ? 'var(--ink)' : 'var(--muted)',
          zIndex: 1,
          overflow: 'hidden'
        }}
      >
        {value ? renderWithMentions(value) : placeholder}
      </div>
      <textarea
        ref={textareaRef}
        className={className}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
        aria-label={ariaLabel}
        required={required}
        onInput={handleInput}
        style={{
          color: 'transparent',
          background: 'transparent',
          caretColor: 'var(--ink)',
          position: 'relative',
          zIndex: 2,
          display: 'block'
        }}
      />
    </div>
  );
};
