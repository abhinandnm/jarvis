import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Terminal, Database, HelpCircle, X, ShieldAlert } from 'lucide-react';

export default function CommandPalette({ isOpen, onClose, onExecuteCommand }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  const commandItems = [
    {
      icon: <Terminal size={14} className="text-cyber-blue" />,
      title: "Run Terminal Command",
      subtitle: "Execute a command prompt task",
      command: "run terminal [command]"
    },
    {
      icon: <Database size={14} className="text-cyber-blue" />,
      title: "Recall Memory Fact",
      subtitle: "Find details stored in Jarvis memory",
      command: "recall fact [category]"
    },
    {
      icon: <ShieldAlert size={14} className="text-orange-500" />,
      title: "Organize Downloads Folder",
      subtitle: "Run files organizer automated sort",
      command: "organize downloads"
    },
    {
      icon: <Search size={14} className="text-cyber-blue" />,
      title: "Find System Files",
      subtitle: "Glob search within user workspace",
      command: "find file [name]"
    },
    {
      icon: <HelpCircle size={14} className="text-slate-400" />,
      title: "Ask JARVIS a Question",
      subtitle: "Direct voice / conversational trigger",
      command: "ask: [question]"
    }
  ];

  const filtered = commandItems.filter(item =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.command.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % filtered.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filtered.length) % filtered.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          handleSelect(filtered[selectedIndex]);
        }
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex]);

  const handleSelect = (item) => {
    onExecuteCommand(item.command);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-cyber-darker/70 backdrop-blur-sm z-50 flex items-start justify-center pt-20 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, y: -10 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: -10 }}
            className="w-full max-w-lg bg-cyber-dark border border-cyber-blue/30 rounded-xl overflow-hidden shadow-[0_0_40px_rgba(0,240,255,0.2)] flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            {/* Input bar */}
            <div className="flex items-center gap-3 px-4 border-b border-cyber-blue/20">
              <Search className="text-cyber-blue" size={16} />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                placeholder="Type a command directive or system query..."
                className="flex-1 bg-transparent py-4 text-xs focus:outline-none placeholder-slate-500 font-mono"
              />
              <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                <X size={16} />
              </button>
            </div>

            {/* List */}
            <div className="max-h-72 overflow-y-auto p-2">
              {filtered.length === 0 ? (
                <div className="p-4 text-center text-slate-500 font-mono text-[10px] uppercase">
                  No matching systems directive found.
                </div>
              ) : (
                filtered.map((item, idx) => (
                  <div
                    key={item.command}
                    onClick={() => handleSelect(item)}
                    className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                      idx === selectedIndex
                        ? 'bg-cyber-blue/15 border border-cyber-blue/30 text-cyber-blue text-glow'
                        : 'hover:bg-cyber-darker/60 text-slate-300 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-1.5 bg-cyber-darker border border-slate-700/50 rounded-md">
                        {item.icon}
                      </div>
                      <div className="text-left">
                        <p className="font-sans font-bold text-xs leading-none mb-1">{item.title}</p>
                        <p className="text-[10px] text-slate-500 font-mono leading-none">{item.subtitle}</p>
                      </div>
                    </div>
                    <span className="font-mono text-[9px] bg-slate-900 px-2 py-1 rounded text-slate-400 border border-slate-800">
                      {item.command}
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Bottom info */}
            <div className="bg-cyber-darker/60 border-t border-cyber-blue/10 px-4 py-2 flex items-center justify-between font-mono text-[8px] text-slate-500 uppercase">
              <span>↑↓ Navigation | Enter Selection</span>
              <span>Esc Close</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
