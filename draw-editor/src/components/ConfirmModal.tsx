import React from 'react';
import { X } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDanger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  isDanger = false,
  onConfirm,
  onCancel
}) => {
  if (!isOpen) return null;

  return (
    <div className="dialog-overlay">
      <dialog className="app-dialog" open>
        <div className="dialog-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">STDD · Confirmação</p>
              <h2>{title}</h2>
            </div>
            <button className="close-btn" onClick={onCancel} type="button">
              <X size={18} />
            </button>
          </div>

          <p className="dialog-copy" style={{ fontSize: '13px', color: 'var(--muted)', marginBottom: '20px', lineHeight: '1.45' }}>
            {message}
          </p>

          <div className="dialog-actions">
            <button type="button" onClick={onCancel}>
              {cancelLabel}
            </button>
            <button
              className={isDanger ? 'primary' : 'primary'} // Styled primary, or we can use styling for danger if desired
              style={isDanger ? { backgroundColor: 'var(--danger)', borderColor: 'var(--danger)', color: '#fff' } : {}}
              type="button"
              onClick={onConfirm}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
};
