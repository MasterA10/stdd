import React, { useState } from 'react';
import { X } from 'lucide-react';

interface ImportExportModalProps {
  mode: 'import' | 'export';
  exportData?: string;
  onClose: () => void;
  onImport: (jsonString: string) => void;
}

export const ImportExportModal: React.FC<ImportExportModalProps> = ({
  mode,
  exportData = '',
  onClose,
  onImport
}) => {
  const [jsonText, setJsonText] = useState(mode === 'export' ? exportData : '');
  const [error, setError] = useState<string | null>(null);

  const handleImportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Validate JSON
      JSON.parse(jsonText);
      onImport(jsonText);
      setError(null);
    } catch (err: any) {
      setError(`JSON Inválido: ${err.message}`);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonText);
    alert('JSON copiado para a área de transferência!');
  };

  return (
    <div className="dialog-overlay">
      <dialog className="app-dialog" open>
        <div className="dialog-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">STDD · Contrato JSON</p>
              <h2>{mode === 'import' ? 'Importar Desenho' : 'Exportar Desenho'}</h2>
            </div>
            <button className="close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          <form onSubmit={handleImportSubmit}>
            <div className="dialog-fields">
              <div className="editor-field">
                <label>Dados JSON</label>
                <textarea
                  className="json-textarea"
                  value={jsonText}
                  onChange={(e) => setJsonText(e.target.value)}
                  readOnly={mode === 'export'}
                  placeholder="Cole o JSON completo do seu contrato de fluxo aqui..."
                  rows={15}
                  required
                />
              </div>
              {error && <div className="error-message">{error}</div>}
            </div>

            <div className="dialog-actions">
              <button type="button" onClick={onClose}>
                Fechar
              </button>
              {mode === 'import' ? (
                <button className="primary" type="submit">
                  Importar
                </button>
              ) : (
                <button className="primary" type="button" onClick={handleCopy}>
                  Copiar JSON
                </button>
              )}
            </div>
          </form>
        </div>
      </dialog>
    </div>
  );
};
