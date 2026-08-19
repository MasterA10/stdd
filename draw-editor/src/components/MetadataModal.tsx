import React, { useState } from 'react';
import { X } from 'lucide-react';

interface MetadataModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { title: string; subtitle: string; kind: string }) => void;
  initialValues?: { title: string; subtitle: string; kind: string };
  titleText: string;
  submitLabel: string;
}

export const MetadataModal: React.FC<MetadataModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialValues = { title: '', subtitle: '', kind: 'feature' },
  titleText,
  submitLabel
}) => {
  const [title, setTitle] = useState(initialValues.title);
  const [subtitle, setSubtitle] = useState(initialValues.subtitle);
  const [kind, setKind] = useState(initialValues.kind);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({
      title: title.trim(),
      subtitle: subtitle.trim(),
      kind
    });
  };

  return (
    <div className="dialog-overlay">
      <dialog className="app-dialog" open>
        <div className="dialog-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">Looper · Metadados do Desenho</p>
              <h2>{titleText}</h2>
            </div>
            <button className="close-btn" onClick={onClose} type="button">
              <X size={18} />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="dialog-fields">
              <div className="editor-field">
                <label>Título do Desenho</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ex: Checkout resiliente"
                  required
                />
              </div>

              <div className="editor-field">
                <label>Descrição / Subtítulo</label>
                <textarea
                  value={subtitle}
                  onChange={(e) => setSubtitle(e.target.value)}
                  placeholder="Descreva o propósito deste diagrama..."
                  rows={4}
                />
              </div>

              <div className="editor-field">
                <label>Tipo do Diagrama</label>
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="feature">Funcionalidade (Feature)</option>
                  <option value="flow">Fluxo (Flow)</option>
                  <option value="architecture">Arquitetura (Architecture)</option>
                  <option value="subflow">Subfluxo (Subflow)</option>
                </select>
              </div>
            </div>

            <div className="dialog-actions">
              <button type="button" onClick={onClose}>
                Cancelar
              </button>
              <button className="primary" type="submit">
                {submitLabel}
              </button>
            </div>
          </form>
        </div>
      </dialog>
    </div>
  );
};
