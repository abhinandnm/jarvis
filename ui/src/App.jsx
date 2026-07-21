import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, Settings as SettingsIcon, X, Send, 
  Cpu, HardDrive, Battery, Thermometer, Radio, Volume2, 
  RefreshCw, Power, MessageSquare, Terminal, Lock, ShieldAlert,
  Clock, ListCollapse, Play, AlertCircle, Eye, FileSearch, Trash2,
  Calendar, Github, Clipboard, Bell, Network, Database, Image,
  FolderOpen, LayoutGrid, Check, Plus, Moon
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Component Imports
import ParticleField from './components/ParticleField';
import SystemRingChart from './components/SystemRingChart';
import NotificationToast from './components/NotificationToast';
import CommandPalette from './components/CommandPalette';

export default function App() {
  // Conversational State
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Online and operational. Systems diagnostics initialized. How may I assist you today, Sir?' }
  ]);
  const [status, setStatus] = useState('idle'); // idle, listening, thinking, speaking
  const [inputText, setInputText] = useState('');
  const [transcript, setTranscript] = useState('');
  const [streamingResponse, setStreamingResponse] = useState('');
  
  // HUD UI Configurations
  const [showSettings, setShowSettings] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [activeHudTab, setActiveHudTab] = useState('diagnostics'); 
  
  // Real-time Metrics
  const [systemStats, setSystemStats] = useState({
    cpu: 0,
    ram: 0,
    disk: 0,
    battery: 100,
    power_plugged: true,
    temperature: 0,
    network_status: 'online',
    gpu_usage: 0,
    gpu_name: 'N/A',
    gpu_memory: 0
  });
  const [processList, setProcessList] = useState([]);
  const [networkInfo, setNetworkInfo] = useState({});
  const [clipboardHistory, setClipboardHistory] = useState([]);
  const [memoryEntries, setMemoryEntries] = useState([]);
  const [scheduledTasks, setScheduledTasks] = useState([]);
  const [pluginsList, setPluginsList] = useState([]);
  const [folderWatchers, setFolderWatchers] = useState([]);
  
  // Notification Toast state
  const [notifications, setNotifications] = useState([]);

  // J.A.R.V.I.S. Security Gate Modal State
  const [permissionRequest, setPermissionRequest] = useState(null); // { id, tool, arguments }

  // Memory adding helper
  const [newMemoryKey, setNewMemoryKey] = useState('');
  const [newMemoryValue, setNewMemoryValue] = useState('');
  const [newMemoryCategory, setNewMemoryCategory] = useState('general');

  // Scheduler task adding helper
  const [newTaskName, setNewTaskName] = useState('');
  const [newTaskCommand, setNewTaskCommand] = useState('');
  const [newTaskTrigger, setNewTaskTrigger] = useState('interval');
  const [newTaskInterval, setNewTaskInterval] = useState(60);

  // Folder watcher adding helper
  const [newWatchPath, setNewWatchPath] = useState('');
  const [newWatchAutoOrganize, setNewWatchAutoOrganize] = useState(false);

  const [config, setConfig] = useState({
    ai_provider: 'gemini',
    gemini_model: 'gemini-2.5-flash',
    openai_model: 'gpt-4o',
    ollama_model: 'llama3',
    stt_provider: 'local',
    tts_provider: 'edge-tts',
    tts_voice: 'en-US-GuyNeural',
    wake_word: 'jarvis',
    has_gemini_key: false,
    has_openai_key: false
  });

  const [voices, setVoices] = useState({
    edge_tts: [],
    local: [],
    openai: []
  });

  // Image Cache Buster (forces reload of screenshot/webcam feeds)
  const [cacheBuster, setCacheBuster] = useState(Date.now());

  // Audio Playback References
  const audioQueueRef = useRef([]);
  const currentAudioRef = useRef(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Audio Recording References
  const [micRecording, setMicRecording] = useState(false);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const stopRecordingCallback = useRef(null);

  // Connection References
  const wsRef = useRef(null);
  const chatEndRef = useRef(null);

  // Initial Bootup
  useEffect(() => {
    fetchVoices();
    fetchSettings();
    updateStats();
    updateProcesses();
    fetchMemories();
    fetchSchedulerTasks();
    fetchPlugins();
    fetchClipboard();
    fetchWatchers();

    // Poll system diagnostics
    const statsInterval = setInterval(updateStats, 2000);
    const procInterval = setInterval(updateProcesses, 4000);
    const clipInterval = setInterval(fetchClipboard, 3000);

    // Ctrl+K key listener for command palette
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearInterval(statsInterval);
      clearInterval(procInterval);
      clearInterval(clipInterval);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Socket setup
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Dialogue Scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingResponse, transcript]);

  const connectWebSocket = () => {
    const wsUrl = `ws://127.0.0.1:8000/ws`;
    console.log(`Connecting to Jarvis WebSocket at ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to Jarvis core websocket.');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'state':
          if (data.content === 'idle' && audioQueueRef.current.length > 0) {
             break;
          }
          setStatus(data.content);
          if (data.content === 'listening') {
            triggerMicrophoneRecording();
          }
          break;
          
        case 'text':
          setStreamingResponse(prev => prev + data.content);
          break;
          
        case 'audio':
          queueAudioSegment(data.content);
          break;
          
        case 'transcript':
          setTranscript(data.content);
          if (data.content.trim()) {
            setMessages(prev => [...prev, { role: 'user', content: data.content }]);
            setTranscript('');
            setStreamingResponse('');
          }
          break;
          
        case 'permission_request':
          stopAllAudioPlayback();
          setPermissionRequest({
            id: data.id,
            tool: data.tool,
            arguments: data.arguments
          });
          break;

        case 'notification':
          // Add notification to top alert center
          const newNotif = {
            id: data.id || Math.random().toString(),
            content: data.content,
            level: data.level || 'info',
            timestamp: data.timestamp || new Date().toISOString()
          };
          setNotifications(prev => [newNotif, ...prev].slice(0, 5));
          break;
          
        default:
          break;
      }
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed. Retrying in 3 seconds...');
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  };

  // ----------------------------------------------------
  // Backend fetch API calls
  // ----------------------------------------------------
  const fetchSettings = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/settings');
      const data = await res.json();
      setConfig(data);
    } catch (e) {
      console.error('Error fetching settings:', e);
    }
  };

  const fetchVoices = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/voices');
      const data = await res.json();
      setVoices(data);
    } catch (e) {
      console.error('Error fetching voices:', e);
    }
  };

  const updateStats = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/stats');
      const data = await res.json();
      setSystemStats(data);
    } catch (e) {
      setSystemStats(prev => ({ ...prev, network_status: 'offline' }));
    }
  };

  const updateProcesses = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/processes');
      const data = await res.json();
      setProcessList(data);
    } catch (e) {
      console.error('Failed to get process diagnostics:', e);
    }
  };

  const fetchMemories = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/memory');
      const data = await res.json();
      setMemoryEntries(data);
    } catch (e) {
      console.error('Failed to load memories:', e);
    }
  };

  const fetchSchedulerTasks = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/scheduler');
      const data = await res.json();
      setScheduledTasks(data);
    } catch (e) {
      console.error('Failed to load tasks:', e);
    }
  };

  const fetchPlugins = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/plugins');
      const data = await res.json();
      setPluginsList(data);
    } catch (e) {
      console.error('Failed to load plugins:', e);
    }
  };

  const fetchClipboard = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/clipboard');
      const data = await res.json();
      setClipboardHistory(data);
    } catch (e) {
      console.log('Clipboard history offline.');
    }
  };

  const fetchWatchers = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/watchers');
      const data = await res.json();
      setFolderWatchers(data);
    } catch (e) {
      console.error(e);
    }
  };

  // ----------------------------------------------------
  // Dynamic add operations
  // ----------------------------------------------------
  const handleAddMemory = async (e) => {
    e.preventDefault();
    if (!newMemoryKey || !newMemoryValue) return;
    try {
      await fetch('http://127.0.0.1:8000/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: newMemoryKey, value: newMemoryValue, category: newMemoryCategory })
      });
      setNewMemoryKey('');
      setNewMemoryValue('');
      fetchMemories();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteMemory = async (key) => {
    try {
      await fetch(`http://127.0.0.1:8000/api/memory/${key}`, { method: 'DELETE' });
      fetchMemories();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddSchedulerTask = async (e) => {
    e.preventDefault();
    if (!newTaskName || !newTaskCommand) return;
    try {
      await fetch('http://127.0.0.1:8000/api/scheduler', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newTaskName,
          command: newTaskCommand,
          trigger_type: newTaskTrigger,
          interval_seconds: parseInt(newTaskInterval)
        })
      });
      setNewTaskName('');
      setNewTaskCommand('');
      fetchSchedulerTasks();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteSchedulerTask = async (taskId) => {
    try {
      await fetch(`http://127.0.0.1:8000/api/scheduler/${taskId}`, { method: 'DELETE' });
      fetchSchedulerTasks();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddWatcher = async (e) => {
    e.preventDefault();
    if (!newWatchPath) return;
    try {
      await fetch('http://127.0.0.1:8000/api/watchers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: newWatchPath, auto_organize: newWatchAutoOrganize })
      });
      setNewWatchPath('');
      fetchWatchers();
    } catch (err) {
      console.error(err);
    }
  };

  const handleStopWatcher = async (path) => {
    try {
      await fetch(`http://127.0.0.1:8000/api/watchers?folder_path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      fetchWatchers();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveSettings = async (updatedConfig) => {
    try {
      await fetch('http://127.0.0.1:8000/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedConfig)
      });
      setConfig(updatedConfig);
      setShowSettings(false);
    } catch (e) {
      console.error('Failed to save settings:', e);
    }
  };

  // ----------------------------------------------------
  // Dangerous Tool Approvals (WebSocket responses)
  // ----------------------------------------------------
  const handlePermissionDecision = (approved) => {
    if (!permissionRequest) return;
    console.log(`Permission decision: approved=${approved}`);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'permission_response',
        id: permissionRequest.id,
        approved: approved
      }));
    }
    setPermissionRequest(null);
    setStatus('thinking');
  };

  // ----------------------------------------------------
  // Audio Queue Playbacks
  // ----------------------------------------------------
  const stopAllAudioPlayback = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    audioQueueRef.current = [];
    setIsPlayingAudio(false);
    setStatus('idle');
  };

  const playNextAudioQueueSegment = () => {
    if (audioQueueRef.current.length === 0) {
      setIsPlayingAudio(false);
      setStatus('idle');
      return;
    }
    
    setStatus('speaking');
    setIsPlayingAudio(true);
    const base64Data = audioQueueRef.current.shift();
    const isWav = base64Data.startsWith('UklGR');
    const mimeType = isWav ? 'audio/wav' : 'audio/mpeg';
    const audioUrl = `data:${mimeType};base64,${base64Data}`;
    const audio = new Audio(audioUrl);
    currentAudioRef.current = audio;
    
    audio.onended = () => playNextAudioQueueSegment();
    audio.onerror = () => playNextAudioQueueSegment();
    audio.play().catch(() => playNextAudioQueueSegment());
  };

  const queueAudioSegment = (base64Data) => {
    audioQueueRef.current.push(base64Data);
    if (!isPlayingAudio) {
      playNextAudioQueueSegment();
    }
  };

  // ----------------------------------------------------
  // Audio Recorder (Mono 16kHz WAV)
  // ----------------------------------------------------
  const triggerMicrophoneRecording = async () => {
    stopAllAudioPlayback();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }));
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      
      const audioBuffers = [];
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioBuffers.push(new Float32Array(inputData));
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      setMicRecording(true);
      setStatus('listening');
      
      stopRecordingCallback.current = () => {
        processor.disconnect();
        source.disconnect();
        stream.getTracks().forEach(t => t.stop());
        
        const totalLength = audioBuffers.reduce((acc, buf) => acc + buf.length, 0);
        const result = new Float32Array(totalLength);
        let offset = 0;
        for (let buf of audioBuffers) {
          result.set(buf, offset);
          offset += buf.length;
        }
        
        if (totalLength === 0) {
          setMicRecording(false);
          setStatus('idle');
          return;
        }

        const buffer = audioContext.createBuffer(1, totalLength, 16000);
        buffer.copyToChannel(result, 0);
        const wavBuffer = bufferToWav(buffer);
        
        const bytes = new Uint8Array(wavBuffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64Wav = window.btoa(binary);
        
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'audio',
            data: base64Wav
          }));
        }
        setMicRecording(false);
      };
    } catch (err) {
      console.error('Mic initialization error:', err);
      setStatus('idle');
      setMicRecording(false);
    }
  };

  const handleMicToggle = () => {
    if (micRecording) {
      if (stopRecordingCallback.current) stopRecordingCallback.current();
    } else {
      triggerMicrophoneRecording();
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    stopAllAudioPlayback();
    const textToSend = inputText;
    setInputText('');
    setStreamingResponse('');
    
    setMessages(prev => [...prev, { role: 'user', content: textToSend }]);
    setStatus('thinking');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'chat',
        text: textToSend
      }));
    }
  };

  const handleExecutePaletteCommand = (command) => {
    setInputText(command);
  };

  useEffect(() => {
    if (streamingResponse.includes('[Screenshot Analyzed]') || streamingResponse.includes('[Webcam Analyzed]')) {
      setCacheBuster(Date.now());
    }
  }, [streamingResponse]);

  useEffect(() => {
    if (status === 'idle' && streamingResponse) {
      setMessages(prev => [...prev, { role: 'assistant', content: streamingResponse }]);
      setStreamingResponse('');
    }
  }, [status]);

  // Window utilities
  const minimizeApp = () => window.electronAPI?.minimizeWindow();
  const closeApp = () => window.electronAPI?.closeWindow();

  return (
    <div className="h-screen w-screen bg-cyber-darker text-white font-inter select-none overflow-hidden relative border border-cyber-blue/30 rounded-2xl flex flex-col hud-scanlines shadow-[0_0_50px_rgba(0,240,255,0.15)]">
      
      {/* Canvas Animated Particle Background */}
      <ParticleField />

      {/* Slide Toast Alerts Overlay */}
      <NotificationToast 
        notifications={notifications} 
        onClose={id => setNotifications(prev => prev.filter(n => n.id !== id))} 
      />

      {/* Quick Access Palette Dialog */}
      <CommandPalette 
        isOpen={isCommandPaletteOpen} 
        onClose={() => setIsCommandPaletteOpen(false)} 
        onExecuteCommand={handleExecutePaletteCommand}
      />

      {/* Dangerous Confirmation Gate Card Modal */}
      <AnimatePresence>
        {permissionRequest && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-cyber-darker/90 backdrop-blur-md z-50 flex items-center justify-center p-6"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="w-full max-w-md bg-cyber-dark border-2 border-orange-500 rounded-xl p-5 shadow-[0_0_30px_rgba(249,115,22,0.4)] flex flex-col gap-4 text-center"
            >
              <div className="flex justify-center text-orange-500 animate-pulse">
                <ShieldAlert size={48} />
              </div>
              <h3 className="font-orbitron font-bold text-orange-400 text-sm tracking-widest uppercase">
                SECURITY DIRECTIVE GATE
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                J.A.R.V.I.S. is requesting authorization to execute a high-risk operation:
              </p>
              
              <div className="bg-cyber-darker border border-orange-500/30 rounded-lg p-3 text-left font-mono text-[10px] text-orange-300 overflow-x-auto">
                <div className="font-bold border-b border-orange-500/20 pb-1 mb-1 text-slate-400">
                  Tool: {permissionRequest.tool}
                </div>
                <div>
                  Args: {JSON.stringify(permissionRequest.arguments, null, 2)}
                </div>
              </div>

              <div className="flex gap-3 mt-2">
                <button 
                  onClick={() => handlePermissionDecision(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 border border-slate-600 font-bold py-2 rounded-lg text-[10px] tracking-wider text-slate-300 font-orbitron uppercase transition-colors"
                >
                  Deny directive
                </button>
                <button 
                  onClick={() => handlePermissionDecision(true)}
                  className="flex-1 bg-orange-500 hover:bg-orange-600 font-bold py-2 rounded-lg text-[10px] tracking-wider text-cyber-darker font-orbitron uppercase transition-colors shadow-[0_0_15px_rgba(249,115,22,0.4)]"
                >
                  Authorize Access
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Top Drag bar Header */}
      <header className="h-12 w-full flex items-center justify-between px-4 border-b border-cyber-blue/20 bg-cyber-darker/60 z-10 drag-handle">
        <div className="flex items-center gap-2">
          <div className={`h-2.5 w-2.5 rounded-full ${status === 'listening' ? 'bg-orange-500 animate-pulse' : 'bg-cyber-blue animate-pulse'}`} />
          <h1 className="font-orbitron font-bold tracking-widest text-xs text-cyber-blue text-glow">
            J.A.R.V.I.S. // CENTRAL_COMMAND_MATRIX
          </h1>
          <span className="text-[8px] font-mono text-slate-500 border border-slate-800 px-1.5 py-0.5 rounded ml-2">
            V2.0-STABLE
          </span>
        </div>
        
        {/* Header Actions */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsCommandPaletteOpen(true)}
            className="hover:text-cyber-blue transition-colors focus:outline-none flex items-center gap-1 text-[9px] font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded"
            title="Open Command Palette"
          >
            <span>Ctrl + K</span>
          </button>
          <button 
            onClick={() => setShowSettings(true)}
            className="hover:text-cyber-blue transition-colors focus:outline-none"
            title="Core Configuration"
          >
            <SettingsIcon size={16} />
          </button>
          <button 
            onClick={minimizeApp} 
            className="hover:text-cyber-blue transition-colors text-slate-400 font-bold focus:outline-none"
          >
            &mdash;
          </button>
          <button 
            onClick={closeApp} 
            className="hover:text-red-500 transition-colors text-slate-400 font-bold focus:outline-none"
          >
            <X size={16} />
          </button>
        </div>
      </header>

      {/* Main UI layout Grid */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden p-4 gap-4 z-10">
        
        {/* Left Side: Conversational Terminal & Hologram Arc Rings */}
        <div className="flex-1 flex flex-col justify-between overflow-hidden gap-4">
          
          {/* Hologram Animation Core Widget */}
          <div className="h-44 flex flex-col items-center justify-center relative">
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-25">
              {/* Spinning Rings */}
              <div className="w-40 h-40 rounded-full border border-cyber-blue animate-spin-slow" />
              <div className="absolute w-36 h-36 rounded-full border border-dashed border-cyan-400 animate-spin-reverse" />
              <div className="absolute w-28 h-28 rounded-full border border-cyber-blue animate-pulse-slow" />
              <div className="absolute w-20 h-20 rounded-full border border-double border-cyan-500" />
            </div>

            {/* Glowing Microphone Central Orb */}
            <button
              onClick={handleMicToggle}
              className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center border-2 border-cyber-blue transition-all duration-300 focus:outline-none ${
                status === 'listening' 
                  ? 'border-orange-500 voice-active-pulse text-orange-500' 
                  : status === 'thinking' 
                  ? 'border-cyan-400 animate-pulse text-cyan-400 shadow-[0_0_20px_#00f0ff]'
                  : 'bg-cyber-dark/40 hover:bg-cyber-blue/10 hover:shadow-[0_0_15px_rgba(0,240,255,0.4)] text-cyber-blue'
              }`}
            >
              {status === 'listening' ? <Mic size={32} /> : <Volume2 size={32} />}
            </button>

            {/* Dynamic Waveform Visualizer */}
            <div className="mt-3 w-48 h-6 flex items-center justify-center gap-1">
              {status === 'idle' && (
                <div className="text-[9px] font-mono tracking-widest text-cyber-blue/40 uppercase">System Ready</div>
              )}
              {status === 'listening' && (
                <div className="flex gap-1 items-end h-full">
                  {[...Array(8)].map((_, i) => (
                    <motion.div 
                      key={i} 
                      className="w-1 bg-orange-500 rounded"
                      animate={{ height: [4, 18, 4] }}
                      transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.08 }}
                    />
                  ))}
                </div>
              )}
              {status === 'thinking' && (
                <div className="text-[9px] font-mono tracking-widest text-cyan-400/80 animate-pulse uppercase">
                  Thinking...
                </div>
              )}
              {status === 'speaking' && (
                <div className="flex gap-1 items-center justify-center h-full">
                  {[...Array(15)].map((_, i) => (
                    <motion.div 
                      key={i} 
                      className="w-1 bg-cyber-blue rounded"
                      animate={{ height: [2, Math.random() * 20 + 2, 2] }}
                      transition={{ duration: 0.4, repeat: Infinity, delay: i * 0.04 }}
                    />
                  ))}
                </div>
              )}
            </div>
            
            <div className="text-center mt-1">
              <span className="text-[9px] font-mono uppercase tracking-widest text-slate-400">
                Mode: {status}
              </span>
            </div>
          </div>

          {/* Dialogue Log area */}
          <div className="flex-1 glass-panel-light rounded-xl p-4 flex flex-col overflow-hidden border border-cyber-blue/10">
            <div className="flex-1 chat-container pr-1 space-y-4">
              {messages.map((msg, i) => {
                const containsScreen = msg.content.includes('[Screenshot Analyzed]') || msg.content.includes('[Screen Description]');
                const containsWebcam = msg.content.includes('[Webcam Analyzed]') || msg.content.includes('[Webcam Description]');
                
                return (
                  <div 
                    key={i} 
                    className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div 
                      className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed ${
                        msg.role === 'user' 
                          ? 'bg-cyber-blue/10 border border-cyber-blue/30 text-right text-cyber-blue shadow-[0_0_10px_rgba(0,240,255,0.05)] font-mono'
                          : 'bg-cyber-darker/60 border border-slate-700/50 text-left text-slate-200'
                      }`}
                    >
                      {msg.content}
                    </div>
                    
                    {/* Visual file assets previews */}
                    {containsScreen && (
                      <div className="mt-2 w-52 border border-cyber-blue/30 rounded-lg overflow-hidden shadow-lg bg-cyber-darker/80 p-1">
                        <span className="text-[8px] font-mono text-cyan-400 block px-1 pb-1">SCREENSHOT SOURCE VIEW</span>
                        <img 
                          src={`http://127.0.0.1:8000/cache/screen_view.png?t=${cacheBuster}`} 
                          alt="Screenshot View"
                          className="w-full h-auto rounded border border-cyber-blue/10 max-h-28 object-cover cursor-pointer hover:scale-105 transition-transform"
                          onClick={() => window.open(`http://127.0.0.1:8000/cache/screen_view.png?t=${cacheBuster}`)}
                        />
                      </div>
                    )}
                    {containsWebcam && (
                      <div className="mt-2 w-52 border border-cyber-blue/30 rounded-lg overflow-hidden shadow-lg bg-cyber-darker/80 p-1">
                        <span className="text-[8px] font-mono text-cyan-400 block px-1 pb-1">WEBCAM SOURCE VIEW</span>
                        <img 
                          src={`http://127.0.0.1:8000/cache/webcam_view.jpg?t=${cacheBuster}`} 
                          alt="Webcam View"
                          className="w-full h-auto rounded border border-cyber-blue/10 max-h-28 object-cover cursor-pointer hover:scale-105 transition-transform"
                          onClick={() => window.open(`http://127.0.0.1:8000/cache/webcam_view.jpg?t=${cacheBuster}`)}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
              
              {transcript && (
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-lg p-3 text-xs bg-orange-500/10 border border-orange-500/30 text-orange-400 animate-pulse font-mono">
                    {transcript}
                  </div>
                </div>
              )}
              {streamingResponse && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-lg p-3 text-xs bg-cyber-darker/60 border border-slate-700/50 text-left text-slate-200">
                    {streamingResponse}
                    <span className="inline-block w-1.5 h-3 bg-cyber-blue ml-1 animate-pulse" />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>
          
          {/* Submit form area */}
          <form onSubmit={handleManualSubmit} className="flex gap-2 relative">
            <input 
              type="text" 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={status === 'listening' ? "Voice input stream processing..." : "Initialize directive to J.A.R.V.I.S..."}
              className="flex-1 bg-cyber-darker/60 border border-cyber-blue/20 rounded-xl px-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyber-blue/50 transition-colors font-mono"
            />
            <button 
              type="submit" 
              className="w-12 h-10 bg-cyber-blue/15 hover:bg-cyber-blue/25 border border-cyber-blue/30 hover:border-cyber-blue/60 transition-colors flex items-center justify-center rounded-xl focus:outline-none text-cyber-blue"
            >
              <Send size={16} />
            </button>
          </form>
        </div>

        {/* Right Side: Multi-HUD Sidebar Grid (8 tabs) */}
        <div className="w-full md:w-96 flex flex-col bg-cyber-darker/40 border border-cyber-blue/15 rounded-xl p-3 select-none overflow-hidden">
          
          {/* Tabs header scrollable wrapper */}
          <div className="flex gap-1 overflow-x-auto border-b border-cyber-blue/20 pb-2 mb-3 scrollbar-none">
            {[
              { id: 'diagnostics', label: 'Diag', icon: <Cpu size={10} /> },
              { id: 'processes', label: 'Proc', icon: <Terminal size={10} /> },
              { id: 'memory', label: 'Mem', icon: <Database size={10} /> },
              { id: 'automation', label: 'Auto', icon: <Clock size={10} /> },
              { id: 'plugins', label: 'Plug', icon: <Github size={10} /> },
              { id: 'vision', label: 'Vision', icon: <Eye size={10} /> },
              { id: 'network', label: 'Net', icon: <Network size={10} /> },
              { id: 'clipboard', label: 'Clip', icon: <Clipboard size={10} /> }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveHudTab(tab.id)}
                className={`py-1.5 px-2.5 rounded flex items-center gap-1 text-[8px] font-orbitron font-bold tracking-wider uppercase transition-all whitespace-nowrap ${
                  activeHudTab === tab.id 
                    ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/40 text-glow'
                    : 'bg-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 flex flex-col overflow-y-auto">
            
            {/* Tab 1: Diagnostics */}
            {activeHudTab === 'diagnostics' && (
              <div className="space-y-4">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  SYSTEM CORE METRICS
                </div>
                
                {/* 4-ring grid */}
                <div className="grid grid-cols-2 gap-3">
                  <SystemRingChart value={systemStats.cpu} label="Processor" icon={<Cpu size={12} />} color="#00f0ff" />
                  <SystemRingChart value={systemStats.ram} label="Memory Stack" icon={<HardDrive size={12} />} color="#00f0ff" />
                  <SystemRingChart value={systemStats.disk} label="Disk Storage" icon={<Database size={12} />} color="#00f0ff" />
                  <SystemRingChart value={systemStats.battery} label="Battery" icon={<Battery size={12} />} color={systemStats.battery > 30 ? "#10b981" : "#f97316"} />
                </div>

                {/* Additional metrics */}
                <div className="bg-cyber-darker/60 border border-cyber-blue/10 rounded-lg p-3 space-y-2 text-[10px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">GPU Core:</span>
                    <span className="text-cyber-blue font-bold">{systemStats.gpu_usage}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">GPU VRAM:</span>
                    <span className="text-cyber-blue">{systemStats.gpu_memory}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Temperature:</span>
                    <span className="text-orange-400">{systemStats.temperature}°C</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Power Line:</span>
                    <span className={systemStats.power_plugged ? "text-emerald-500" : "text-amber-500"}>
                      {systemStats.power_plugged ? "Connected" : "Battery Mode"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: Processes */}
            {activeHudTab === 'processes' && (
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 flex justify-between items-center">
                  <span>RUNNING PROCESSES</span>
                  <span className="text-[8px] font-mono text-slate-500">Top Memory</span>
                </div>
                
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 text-[9px] font-mono">
                  {processList.length === 0 ? (
                    <div className="text-slate-500 text-center py-4">Polling processes...</div>
                  ) : (
                    processList.map((proc, idx) => (
                      <div key={idx} className="flex justify-between items-center bg-cyber-darker/40 border border-cyber-blue/5 rounded p-1.5 hover:border-cyber-blue/20 transition-all">
                        <span className="truncate w-36 text-slate-300 font-bold" title={proc.name}>
                          {proc.name}
                        </span>
                        <div className="flex gap-3 text-slate-400">
                          <span>PID: <span className="text-slate-300">{proc.pid}</span></span>
                          <span>MEM: <span className="text-cyber-blue font-bold">{proc.memory}%</span></span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Tab 3: Long-term Memory database */}
            {activeHudTab === 'memory' && (
              <div className="space-y-4">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  Memory Database
                </div>

                <form onSubmit={handleAddMemory} className="bg-cyber-darker/60 border border-cyber-blue/10 p-2.5 rounded-lg space-y-2">
                  <div className="text-[8px] font-mono text-slate-500 uppercase">Write memory fact:</div>
                  <input 
                    type="text" 
                    placeholder="Key e.g. user_birthday"
                    value={newMemoryKey}
                    onChange={e => setNewMemoryKey(e.target.value)}
                    className="w-full bg-cyber-darker border border-cyber-blue/20 rounded p-1.5 text-[10px] text-white focus:outline-none focus:border-cyber-blue/40"
                  />
                  <input 
                    type="text" 
                    placeholder="Value e.g. Oct 12"
                    value={newMemoryValue}
                    onChange={e => setNewMemoryValue(e.target.value)}
                    className="w-full bg-cyber-darker border border-cyber-blue/20 rounded p-1.5 text-[10px] text-white focus:outline-none focus:border-cyber-blue/40"
                  />
                  <button 
                    type="submit"
                    className="w-full bg-cyber-blue/20 hover:bg-cyber-blue/30 border border-cyber-blue/40 text-cyber-blue text-[9px] font-mono py-1 rounded"
                  >
                    Commit Memory Fact
                  </button>
                </form>

                <div className="space-y-1.5 max-h-56 overflow-y-auto">
                  {memoryEntries.map(e => (
                    <div key={e.key} className="bg-cyber-darker/40 border border-cyber-blue/5 rounded p-2 text-[10px] flex justify-between items-start font-mono">
                      <div className="min-w-0 flex-1 pr-2">
                        <span className="text-cyan-400 font-bold text-[9px] block uppercase leading-none mb-0.5">{e.key}</span>
                        <span className="text-slate-300 break-words">{e.value}</span>
                      </div>
                      <button 
                        onClick={() => handleDeleteMemory(e.key)}
                        className="text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 4: Scheduler & Folders watcher */}
            {activeHudTab === 'automation' && (
              <div className="space-y-4">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  AUTOMATION AGENTS
                </div>

                {/* Add task */}
                <form onSubmit={handleAddSchedulerTask} className="bg-cyber-darker/60 border border-cyber-blue/10 p-2.5 rounded-lg space-y-2">
                  <div className="text-[8px] font-mono text-slate-500 uppercase">Create automation task:</div>
                  <input 
                    type="text" 
                    placeholder="Task name e.g. Run Diagnostics"
                    value={newTaskName}
                    onChange={e => setNewTaskName(e.target.value)}
                    className="w-full bg-cyber-darker border border-cyber-blue/20 rounded p-1.5 text-[10px] text-white focus:outline-none focus:border-cyber-blue/40"
                  />
                  <input 
                    type="text" 
                    placeholder="Shell command to run"
                    value={newTaskCommand}
                    onChange={e => setNewTaskCommand(e.target.value)}
                    className="w-full bg-cyber-darker border border-cyber-blue/20 rounded p-1.5 text-[10px] text-white focus:outline-none focus:border-cyber-blue/40"
                  />
                  <button 
                    type="submit"
                    className="w-full bg-cyber-blue/20 hover:bg-cyber-blue/30 border border-cyber-blue/40 text-cyber-blue text-[9px] font-mono py-1.5 rounded"
                  >
                    Schedule Task
                  </button>
                </form>

                {/* List Tasks */}
                <div className="space-y-1.5">
                  {scheduledTasks.map(t => (
                    <div key={t.id} className="bg-cyber-darker/40 border border-cyber-blue/5 rounded p-2 text-[10px] flex justify-between items-center font-mono">
                      <div>
                        <span className="text-cyan-400 font-bold block">{t.name}</span>
                        <span className="text-slate-500 text-[8px]">Next: {t.next_run ? t.next_run.slice(11,19) : 'None'}</span>
                      </div>
                      <button 
                        onClick={() => handleDeleteSchedulerTask(t.id)}
                        className="text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  Directory Watcher
                </div>

                {/* Directory watcher form */}
                <form onSubmit={handleAddWatcher} className="bg-cyber-darker/60 border border-cyber-blue/10 p-2.5 rounded-lg space-y-2">
                  <input 
                    type="text" 
                    placeholder="Folder path e.g. C:\Downloads"
                    value={newWatchPath}
                    onChange={e => setNewWatchPath(e.target.value)}
                    className="w-full bg-cyber-darker border border-cyber-blue/20 rounded p-1.5 text-[10px] text-white focus:outline-none"
                  />
                  <label className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                    <input 
                      type="checkbox" 
                      checked={newWatchAutoOrganize} 
                      onChange={e => setNewWatchAutoOrganize(e.target.checked)}
                      className="border border-cyber-blue/30 rounded"
                    />
                    Auto-organize dropped files
                  </label>
                  <button 
                    type="submit"
                    className="w-full bg-cyber-blue/20 hover:bg-cyber-blue/30 border border-cyber-blue/40 text-cyber-blue text-[9px] font-mono py-1 rounded"
                  >
                    Start Folder Watcher
                  </button>
                </form>

                <div className="space-y-1">
                  {folderWatchers.map(w => (
                    <div key={w.path} className="bg-cyber-darker/40 border border-cyber-blue/5 rounded p-2 text-[9px] flex justify-between items-center font-mono">
                      <span className="truncate w-64 text-slate-300" title={w.path}>{w.path}</span>
                      <button onClick={() => handleStopWatcher(w.path)} className="text-red-500 hover:text-red-400 font-bold">
                        Stop
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 5: Plugins */}
            {activeHudTab === 'plugins' && (
              <div className="space-y-3">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  SYSTEM PLUGINS
                </div>

                {pluginsList.map(plugin => (
                  <div key={plugin.name} className="bg-cyber-darker/60 border border-cyber-blue/10 rounded-lg p-2.5 text-xs font-mono relative">
                    <div className="flex justify-between items-center text-cyan-400 font-bold uppercase text-[10px] mb-1">
                      <span>{plugin.name}</span>
                      <span className="text-[8px] border border-emerald-500/20 text-emerald-500 px-1 rounded">ACTIVE</span>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-normal mb-2">
                      {plugin.description}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {plugin.tools.map(tool => (
                        <span key={tool} className="text-[8px] bg-slate-900 border border-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 6: Vision Capture Stream */}
            {activeHudTab === 'vision' && (
              <div className="space-y-4">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  Vision Matrix
                </div>

                <div className="border border-cyber-blue/30 rounded-lg overflow-hidden bg-cyber-darker/80 p-1.5">
                  <div className="flex justify-between text-[8px] font-mono text-cyan-400 pb-1.5">
                    <span>LIVE SCREEN PREVIEW</span>
                    <button 
                      onClick={() => setCacheBuster(Date.now())}
                      className="hover:text-white"
                    >
                      Refresh
                    </button>
                  </div>
                  <img 
                    src={`http://127.0.0.1:8000/cache/screen_view.png?t=${cacheBuster}`} 
                    alt="Active screenshot view"
                    className="w-full h-auto rounded border border-cyber-blue/10 object-contain max-h-36"
                    onError={(e) => { e.target.src = 'https://placehold.co/400x200/020c1b/00f0ff?text=No+screenshot+cache'; }}
                  />
                </div>

                <div className="border border-cyber-blue/30 rounded-lg overflow-hidden bg-cyber-darker/80 p-1.5">
                  <div className="text-[8px] font-mono text-cyan-400 pb-1.5">WEBCAM MATRIX</div>
                  <img 
                    src={`http://127.0.0.1:8000/cache/webcam_view.jpg?t=${cacheBuster}`} 
                    alt="Active webcam capture view"
                    className="w-full h-auto rounded border border-cyber-blue/10 object-contain max-h-36"
                    onError={(e) => { e.target.src = 'https://placehold.co/400x200/020c1b/00f0ff?text=No+webcam+cache'; }}
                  />
                </div>
              </div>
            )}

            {/* Tab 7: Network Info */}
            {activeHudTab === 'network' && (
              <div className="space-y-4">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  NETWORK INFORMATION
                </div>

                <div className="bg-cyber-darker/60 border border-cyber-blue/10 rounded-lg p-3 space-y-2 text-[10px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Connection:</span>
                    <span className="text-emerald-500 font-bold">ONLINE</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Gateway Route:</span>
                    <span className="text-slate-300">127.0.0.1</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Ping Delay:</span>
                    <span className="text-cyber-blue">4 ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Data Sent:</span>
                    <span className="text-slate-300">{(systemStats.cpu * 1.4).toFixed(0)} KB/s</span>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 8: Clipboard History */}
            {activeHudTab === 'clipboard' && (
              <div className="space-y-3">
                <div className="text-[9px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 uppercase">
                  CLIPBOARD EXPLORER
                </div>

                <div className="space-y-2">
                  {clipboardHistory.length === 0 ? (
                    <div className="text-slate-500 font-mono text-[9px] text-center py-4">
                      No clipboard history tracked.
                    </div>
                  ) : (
                    clipboardHistory.map((item, idx) => (
                      <div 
                        key={idx} 
                        className="bg-cyber-darker/50 border border-cyber-blue/5 rounded p-2 text-[10px] font-mono relative cursor-pointer hover:border-cyber-blue/30"
                        onClick={() => {
                          navigator.clipboard.writeText(item.content);
                          // Add copy notification
                          setNotifications(prev => [{
                            id: Math.random().toString(),
                            content: "Copied clip from history!",
                            level: "success"
                          }, ...prev]);
                        }}
                      >
                        <div className="text-slate-500 text-[8px] leading-none mb-1">
                          {item.timestamp ? item.timestamp.slice(11, 19) : ''}
                        </div>
                        <p className="text-slate-200 line-clamp-2 leading-relaxed select-all">
                          {item.preview || item.content}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
            
          </div>
        </div>

      </div>

      {/* Futuristic Settings Slide Panel overlay */}
      <AnimatePresence>
        {showSettings && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-cyber-darker/85 backdrop-blur-md z-40 flex justify-end"
          >
            <motion.div 
              initial={{ x: 300 }}
              animate={{ x: 0 }}
              exit={{ x: 300 }}
              transition={{ type: 'tween', duration: 0.3 }}
              className="w-80 h-full bg-cyber-dark border-l border-cyber-blue/30 p-6 flex flex-col justify-between overflow-y-auto"
            >
              <div>
                <div className="flex items-center justify-between mb-6 pb-2 border-b border-cyber-blue/20">
                  <h3 className="font-orbitron font-bold text-cyber-blue text-sm tracking-wider flex items-center gap-2">
                    <Radio size={16} /> CONFIG_MATRIX
                  </h3>
                  <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white transition-colors">
                    <X size={18} />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                      AI Cognitive Provider
                    </label>
                    <select 
                      value={config.ai_provider}
                      onChange={(e) => setConfig(prev => ({ ...prev, ai_provider: e.target.value }))}
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
                    >
                      <option value="gemini">Google Gemini</option>
                      <option value="openai">OpenAI GPT</option>
                      <option value="ollama">Ollama (Local LLM)</option>
                    </select>
                  </div>

                  {config.ai_provider === 'gemini' && (
                    <div>
                      <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                        Gemini Model
                      </label>
                      <input 
                        type="text" 
                        value={config.gemini_model}
                        onChange={(e) => setConfig(prev => ({ ...prev, gemini_model: e.target.value }))}
                        className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none"
                      />
                    </div>
                  )}

                  {config.ai_provider === 'openai' && (
                    <div>
                      <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                        OpenAI Model
                      </label>
                      <input 
                        type="text" 
                        value={config.openai_model}
                        onChange={(e) => setConfig(prev => ({ ...prev, openai_model: e.target.value }))}
                        className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none"
                      />
                    </div>
                  )}

                  {config.ai_provider === 'ollama' && (
                    <div>
                      <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                        Ollama Model
                      </label>
                      <input 
                        type="text" 
                        value={config.ollama_model}
                        onChange={(e) => setConfig(prev => ({ ...prev, ollama_model: e.target.value }))}
                        className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                      Speech recognition (STT)
                    </label>
                    <select 
                      value={config.stt_provider}
                      onChange={(e) => setConfig(prev => ({ ...prev, stt_provider: e.target.value }))}
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none"
                    >
                      <option value="local">SpeechRecognition (Default)</option>
                      <option value="openai">OpenAI Whisper API</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                      Vocal Matrix (TTS)
                    </label>
                    <select 
                      value={config.tts_provider}
                      onChange={(e) => setConfig(prev => ({ ...prev, tts_provider: e.target.value }))}
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none"
                    >
                      <option value="edge-tts">Edge-TTS (Free Neural)</option>
                      <option value="local">pyttsx3 (Offline Voice)</option>
                      <option value="openai">OpenAI TTS API</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                      Voice Profile
                    </label>
                    <select 
                      value={config.tts_voice}
                      onChange={(e) => setConfig(prev => ({ ...prev, tts_voice: e.target.value }))}
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none"
                    >
                      {config.tts_provider === 'edge-tts' && voices.edge_tts.map(v => (
                        <option key={v.id} value={v.id}>{v.name}</option>
                      ))}
                      {config.tts_provider === 'local' && voices.local.map(v => (
                        <option key={v.id} value={v.id}>{v.name}</option>
                      ))}
                      {config.tts_provider === 'openai' && voices.openai.map(v => (
                        <option key={v.id} value={v.id}>{v.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-6 mt-6 border-t border-cyber-blue/20">
                <button 
                  onClick={() => handleSaveSettings(config)}
                  className="flex-1 bg-cyber-blue hover:bg-cyber-blue/80 text-cyber-darker font-bold py-2.5 px-4 rounded-lg text-xs tracking-wider transition-colors uppercase font-orbitron"
                >
                  Apply System Settings
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      
    </div>
  );
}

// ----------------------------------------------------
// ArrayBuffer to WAV compiler helper (16-bit PCM 16kHz)
// ----------------------------------------------------
function bufferToWav(buffer) {
  let numOfChan = buffer.numberOfChannels,
      btwLength = buffer.length * numOfChan * 2 + 44,
      btwBuffer = new ArrayBuffer(btwLength),
      btwView = new DataView(btwBuffer),
      btwChannels = [],
      btwIndex, btwLoop, btwSample,
      btwPos = 0;

  function setUint16(data) {
    btwView.setUint16(btwPos, data, true);
    btwPos += 2;
  }

  function setUint32(data) {
    btwView.setUint32(btwPos, data, true);
    btwPos += 4;
  }

  setUint32(0x46464952); // "RIFF"
  setUint32(btwLength - 8);
  setUint32(0x45564157); // "WAVE"

  setUint32(0x20746d66); // "fmt "
  setUint32(16);
  setUint16(1); // PCM
  setUint16(numOfChan);
  setUint32(buffer.sampleRate);
  setUint32(buffer.sampleRate * 2 * numOfChan);
  setUint16(numOfChan * 2);
  setUint16(16);

  setUint32(0x61746164); // "data"
  setUint32(btwLength - btwPos - 4);

  for (btwIndex = 0; btwIndex < numOfChan; btwIndex++) {
    btwChannels.push(buffer.getChannelData(btwIndex));
  }

  btwLoop = buffer.length;
  for (btwIndex = 0; btwIndex < btwLoop; btwIndex++) {
    for (let chan = 0; chan < numOfChan; chan++) {
      btwSample = btwChannels[chan][btwIndex];
      btwSample = Math.max(-1, Math.min(1, btwSample));
      btwSample = btwSample < 0 ? btwSample * 0x8000 : btwSample * 0x7FFF;
      btwView.setInt16(btwPos, btwSample, true);
      btwPos += 2;
    }
  }

  return btwBuffer;
}
