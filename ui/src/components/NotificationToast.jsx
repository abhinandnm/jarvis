import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, AlertTriangle, CheckCircle, XCircle, X } from 'lucide-react';

export default function NotificationToast({ notifications, onClose }) {
  const getIcon = (level) => {
    switch (level) {
      case 'warning':
        return <AlertTriangle className="text-orange-500" size={16} />;
      case 'error':
        return <XCircle className="text-red-500" size={16} />;
      case 'success':
        return <CheckCircle className="text-emerald-500" size={16} />;
      default:
        return <Info className="text-cyber-blue" size={16} />;
    }
  };

  const getBorderColor = (level) => {
    switch (level) {
      case 'warning':
        return 'border-orange-500/30 shadow-[0_0_15px_rgba(249,115,22,0.15)]';
      case 'error':
        return 'border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.15)]';
      case 'success':
        return 'border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]';
      default:
        return 'border-cyber-blue/30 shadow-[0_0_15px_rgba(0,240,255,0.15)]';
    }
  };

  return (
    <div className="absolute top-16 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {notifications.map((n) => (
          <motion.div
            key={n.id}
            initial={{ opacity: 0, x: 50, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 30, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className={`pointer-events-auto bg-cyber-dark/85 backdrop-blur-md border rounded-xl p-3 flex items-start gap-3 ${getBorderColor(
              n.level
            )}`}
          >
            <div className="mt-0.5">{getIcon(n.level)}</div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest leading-none mb-1">
                {n.level || 'notification'}
              </p>
              <p className="text-xs text-slate-200 leading-normal font-sans">{n.content}</p>
            </div>
            <button
              onClick={() => onClose(n.id)}
              className="text-slate-500 hover:text-white transition-colors"
            >
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
