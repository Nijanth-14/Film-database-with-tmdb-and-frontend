import React from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';
import './ConfirmModal.css';

export default function ConfirmModal({ isOpen, title, message, confirmText, cancelText, onConfirm, onCancel, variant }) {
  const isDestructive = variant === 'destructive';

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="confirm-overlay"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.98, opacity: 0, y: 16 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.982, opacity: 0, y: 10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="confirm-panel"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button className="confirm-close" onClick={onCancel}>
              <X size={16} />
            </button>

            {/* Icon */}
            <div className={`confirm-icon-ring ${isDestructive ? 'confirm-icon-ring--destructive' : ''}`}>
              <AlertTriangle size={22} strokeWidth={2.2} />
            </div>

            {/* Text */}
            <h3 className="confirm-title">{title || 'Are you sure?'}</h3>
            <p className="confirm-message">{message || 'This action cannot be undone.'}</p>

            {/* Actions */}
            <div className="confirm-actions">
              <button className="confirm-btn confirm-btn--cancel" onClick={onCancel}>
                {cancelText || 'Cancel'}
              </button>
              <button
                className={`confirm-btn ${isDestructive ? 'confirm-btn--destructive' : 'confirm-btn--primary'}`}
                onClick={onConfirm}
              >
                {confirmText || 'Confirm'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null;
}
