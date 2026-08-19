import { useRef, useEffect, useState } from 'react';

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
  const [isFocused, setIsFocused] = useState(false);
  const hasMentions = /(@stdd|@developer|@obs)/i.test(value || '');
  const useHighlightLayer = hasMentions && !isFocused;

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
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          whiteSpace: 'pre-wrap',
          wordWrap: 'break-word',
          overflowWrap: 'anywhere',
          color: value ? 'var(--ink)' : 'var(--muted)',
          zIndex: 1,
          overflow: 'hidden',
          opacity: useHighlightLayer ? 1 : 0
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
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        style={{
          color: useHighlightLayer ? 'transparent' : 'var(--ink)',
          background: useHighlightLayer ? 'transparent' : 'var(--input-bg)',
          caretColor: 'var(--ink)',
          position: 'relative',
          zIndex: 2,
          display: 'block'
        }}
      />
    </div>
  );
};
