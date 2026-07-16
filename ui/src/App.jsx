import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, Settings as SettingsIcon, X, Send, 
  Cpu, HardDrive, Battery, Thermometer, Radio, Volume2, 
  RefreshCw, Power, MessageSquare, Terminal, Lock, ShieldAlert,
  Clock, ListCollapse, Play, AlertCircle, Eye, FileSearch, Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function App() {
  // Conversational State
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Online and operational. Hover grids are calibrated. How may I assist you today, Sir?' }
  ]);
  const [status, setStatus] = useState('idle'); // idle, listening, thinking, speaking
  const [inputText, setInputText] = useState('');
  const [transcript, setTranscript] = useState('');
  const [streamingResponse, setStreamingResponse] = useState('');
  
  // HUD UI Configurations
  const [showSettings, setShowSettings] = useState(false);
  const [activeHudTab, setActiveHudTab] = useState('diagnostics'); // diagnostics, processes, scheduler
  
  // Real-time Metrics
  const [systemStats, setSystemStats] = useState({
    cpu: 0,
    ram: 0,
    disk: 0,
    battery: 100,
    power_plugged: true,
    temperature: 0,
    network_status: 'online'
  });
  const [processList, setProcessList] = useState([]);
  
  // J.A.R.V.I.S. Security Gate Modal State
  const [permissionRequest, setPermissionRequest] = useState(null); // { id, tool, arguments }

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

    // Poll system diagnostics
    const statsInterval = setInterval(updateStats, 2500);
    const procInterval = setInterval(updateProcesses, 4000);

    return () => {
      clearInterval(statsInterval);
      clearInterval(procInterval);
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
          // Halt assistant voice queue and prompt authorization card
          stopAllAudioPlayback();
          setPermissionRequest({
            id: data.id,
            tool: data.tool,
            arguments: data.arguments
          });
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
    
    console.log(`Sending authorization decision: approved=${approved} for request ${permissionRequest.id}`);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'permission_response',
        id: permissionRequest.id,
        approved: approved
      }));
    }
    
    // Clear prompt card
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
    
    const audioUrl = `data:audio/mp3;base64,${base64Data}`;
    const audio = new Audio(audioUrl);
    currentAudioRef.current = audio;
    
    audio.onended = () => {
      playNextAudioQueueSegment();
    };
    
    audio.onerror = () => {
      playNextAudioQueueSegment();
    };
    
    audio.play().catch(err => {
      playNextAudioQueueSegment();
    });
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
      if (stopRecordingCallback.current) {
        stopRecordingCallback.current();
      }
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

  // Helper trigger to trigger visual cache reload on screenshot/webcam trace
  useEffect(() => {
    if (streamingResponse.includes('[Screenshot Analyzed]') || streamingResponse.includes('[Webcam Analyzed]')) {
      setCacheBuster(Date.now());
    }
  }, [streamingResponse]);

  // Clean final tokens aggregation
  useEffect(() => {
    if (status === 'idle' && streamingResponse) {
      setMessages(prev => [...prev, { role: 'assistant', content: streamingResponse }]);
      setStreamingResponse('');
    }
  }, [status]);

  // Window utilities
  const minimizeApp = () => window.electronAPI?.minimizeWindow();
  const closeApp = () => window.electronAPI?.closeWindow();

  // Organizer manual dispatch helper
  const handleQuickOrganize = async () => {
    stopAllAudioPlayback();
    setStatus('thinking');
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'chat',
        text: 'Organize my Downloads directory'
      }));
    }
  };

  return (
    <div className="h-screen w-screen glass-panel rounded-2xl flex flex-col overflow-hidden border border-cyber-blue/30 hud-scanlines text-white font-inter select-none relative">
      
      {/* ---------------------------------------------------- */}
      {/* Dynamic Authorization Modal Card Overlay             */}
      {/* ---------------------------------------------------- */}
      <AnimatePresence>
        {permissionRequest && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-cyber-darker/90 backdrop-blur-md z-40 flex items-center justify-center p-6"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="w-full max-w-sm bg-cyber-dark border-2 border-orange-500 rounded-xl p-5 shadow-[0_0_30px_rgba(249,115,22,0.4)] flex flex-col gap-4 text-center"
            >
              <div className="flex justify-center text-orange-500 animate-pulse">
                <ShieldAlert size={48} />
              </div>
              <h3 className="font-orbitron font-bold text-orange-400 text-sm tracking-widest uppercase">
                SECURITY DIRECTIVE GATE
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                J.A.R.V.I.S. is requesting confirmation to execute a high-risk operation:
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

      {/* Top Header */}
      <header className="h-12 w-full flex items-center justify-between px-4 border-b border-cyber-blue/20 bg-cyber-darker/60 z-10 drag-handle">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${status === 'listening' ? 'bg-orange-500 animate-pulse' : 'bg-cyber-blue animate-pulse'}`} />
          <h1 className="font-orbitron font-bold tracking-widest text-xs text-cyber-blue text-glow">
            J.A.R.V.I.S. // CENTRAL_HUD
          </h1>
        </div>
        
        {/* Header Actions */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowSettings(true)}
            className="hover:text-cyber-blue transition-colors focus:outline-none"
            title="Systems Matrix Setup"
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

      {/* Grid HUD Layout */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden p-4 gap-4">
        
        {/* Chat / Hologram Widget Pane */}
        <div className="flex-1 flex flex-col justify-between overflow-hidden gap-4">
          
          {/* Hologram Circle */}
          <div className="h-44 flex flex-col items-center justify-center relative">
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
              <div className="w-40 h-40 rounded-full border border-cyber-blue animate-spin-slow" />
              <div className="absolute w-32 h-32 rounded-full border border-dashed border-cyber-blue animate-spin-reverse" />
              <div className="absolute w-24 h-24 rounded-full border border-cyber-blue animate-pulse-slow" />
            </div>

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

            {/* Waveforms */}
            <div className="mt-3 w-48 h-6 flex items-center justify-center gap-1">
              {status === 'idle' && (
                <div className="text-[10px] font-mono tracking-widest text-cyber-blue/40 uppercase">System Calibrated</div>
              )}
              {status === 'listening' && (
                <div className="flex gap-1 items-end h-full">
                  {[...Array(6)].map((_, i) => (
                    <motion.div 
                      key={i} 
                      className="w-1 bg-orange-500 rounded"
                      animate={{ height: [4, 16, 4] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }}
                    />
                  ))}
                </div>
              )}
              {status === 'thinking' && (
                <div className="text-[10px] font-mono tracking-widest text-cyan-400/80 animate-pulse uppercase">
                  ACCESSING KNOWLEDGE MATRIX
                </div>
              )}
              {status === 'speaking' && (
                <div className="flex gap-1 items-center justify-center h-full">
                  {[...Array(12)].map((_, i) => (
                    <motion.div 
                      key={i} 
                      className="w-1 bg-cyber-blue rounded"
                      animate={{ height: [2, Math.random() * 20 + 2, 2] }}
                      transition={{ duration: 0.4, repeat: Infinity, delay: i * 0.05 }}
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
                          ? 'bg-cyber-blue/10 border border-cyber-blue/30 text-right text-cyber-blue shadow-[0_0_10px_rgba(0,240,255,0.05)]'
                          : 'bg-cyber-darker/60 border border-slate-700/50 text-left text-slate-200'
                      }`}
                    >
                      {msg.content}
                    </div>
                    
                    {/* Multimodal image preview renders */}
                    {containsScreen && (
                      <div className="mt-2 w-48 border border-cyber-blue/30 rounded-lg overflow-hidden shadow-lg bg-cyber-darker/80 p-1 animate-fadeIn">
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
                      <div className="mt-2 w-48 border border-cyber-blue/30 rounded-lg overflow-hidden shadow-lg bg-cyber-darker/80 p-1 animate-fadeIn">
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
                  <div className="max-w-[85%] rounded-lg p-3 text-xs bg-orange-500/10 border border-orange-500/30 text-orange-400 animate-pulse">
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
          
          {/* Form manual trigger */}
          <form onSubmit={handleManualSubmit} className="flex gap-2 relative">
            <input 
              type="text" 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={status === 'listening' ? "Verbal processing stream active..." : "Initiate command directive, Sir..."}
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

        {/* ---------------------------------------------------- */}
        {/* Dynamic Multi-HUD Sidebar Tab System                 */}
        {/* ---------------------------------------------------- */}
        <div className="w-full md:w-96 flex flex-col bg-cyber-darker/40 border border-cyber-blue/15 rounded-xl p-3 select-none overflow-hidden">
          
          {/* Tabs Selector Header */}
          <div className="grid grid-cols-3 gap-1.5 border-b border-cyber-blue/20 pb-2 mb-3">
            {['diagnostics', 'processes', 'scheduler'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveHudTab(tab)}
                className={`py-1.5 rounded text-[8px] font-orbitron font-bold tracking-widest uppercase transition-all ${
                  activeHudTab === tab 
                    ? 'bg-cyber-blue/20 text-cyber-blue border border-cyber-blue/40 text-glow'
                    : 'bg-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex-1 flex flex-col overflow-y-auto">
            {/* Tab: Diagnostics */}
            {activeHudTab === 'diagnostics' && (
              <div className="space-y-4">
                <div className="text-[10px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1">
                  SYSTEM CORE METRICS
                </div>
                {/* CPU */}
                <div>
                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><Cpu size={10} /> PROCESSOR</span>
                    <span>{Math.round(systemStats.cpu)}%</span>
                  </div>
                  <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-cyber-blue shadow-[0_0_8px_#00f0ff] transition-all duration-500" style={{ width: `${systemStats.cpu}%` }} />
                  </div>
                </div>
                {/* RAM */}
                <div>
                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><HardDrive size={10} /> MEMORY STACK</span>
                    <span>{Math.round(systemStats.ram)}%</span>
                  </div>
                  <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-cyber-blue shadow-[0_0_8px_#00f0ff] transition-all duration-500" style={{ width: `${systemStats.ram}%` }} />
                  </div>
                </div>
                {/* TEMP */}
                <div>
                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><Thermometer size={10} /> TEMPERATURE</span>
                    <span>{Math.round(systemStats.temperature)}&deg;C</span>
                  </div>
                  <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-cyber-blue shadow-[0_0_8px_#00f0ff] transition-all duration-500" style={{ width: `${Math.min(100, Math.max(0, systemStats.temperature))}%` }} />
                  </div>
                </div>
                {/* BATT */}
                <div>
                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><Battery size={10} /> CELL BATTERY</span>
                    <span>{systemStats.battery}%</span>
                  </div>
                  <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-cyber-blue shadow-[0_0_8px_#00f0ff] transition-all duration-500" style={{ width: `${systemStats.battery}%` }} />
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Processes */}
            {activeHudTab === 'processes' && (
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="text-[10px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1 flex justify-between items-center">
                  <span>RUNNING PROCESSES</span>
                  <span className="text-[8px] font-mono text-slate-500">Top Memory</span>
                </div>
                
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 text-[9px] font-mono">
                  {processList.length === 0 ? (
                    <div className="text-slate-500 text-center py-4">Polling processes...</div>
                  ) : (
                    processList.map((proc, idx) => (
                      <div key={idx} className="flex justify-between items-center bg-cyber-darker/40 border border-cyber-blue/5 rounded p-1.5">
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

            {/* Tab: Scheduler & Automation */}
            {activeHudTab === 'scheduler' && (
              <div className="space-y-4">
                <div className="text-[10px] font-orbitron tracking-widest text-cyber-blue/60 mb-2 border-b border-cyber-blue/10 pb-1">
                  AUTOMATION AGENTS
                </div>
                
                {/* Downloads Watcher Card */}
                <div className="bg-cyber-darker/60 border border-cyber-blue/10 rounded-lg p-2.5 space-y-1 text-xs">
                  <div className="flex justify-between items-center font-orbitron font-bold text-[10px] text-cyber-blue">
                    <span className="flex items-center gap-1"><Clock size={10} /> DOWNLOADS ORGANIZER</span>
                    <span className="text-emerald-500 text-[8px] border border-emerald-500/20 px-1 rounded">ACTIVE</span>
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Directory watcher actively scans and organizes downloaded files based on file extensions.
                  </p>
                  <button 
                    onClick={handleQuickOrganize}
                    className="w-full mt-2 bg-cyber-blue/10 hover:bg-cyber-blue/20 border border-cyber-blue/30 text-cyber-blue font-mono font-bold py-1.5 rounded text-[9px] tracking-wider uppercase transition-all"
                  >
                    Force Sort Directory
                  </button>
                </div>

                {/* Scheduled diagnostics card */}
                <div className="bg-cyber-darker/60 border border-cyber-blue/10 rounded-lg p-2.5 space-y-1 text-xs opacity-75">
                  <div className="flex justify-between items-center font-orbitron font-bold text-[10px] text-slate-400">
                    <span className="flex items-center gap-1"><Clock size={10} /> RECURRING_DIAGNOSTICS</span>
                    <span className="text-slate-500 text-[8px]">INTERVAL (30s)</span>
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Automatically checks core temperatures and logs anomalies to standard SQLite memory stack.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Settings Panel */}
      <AnimatePresence>
        {showSettings && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-cyber-darker/85 backdrop-blur-md z-30 flex justify-end"
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
                        className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
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
                        className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
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
                        className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
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
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
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
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
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
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
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

                  <div>
                    <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1.5">
                      Wake Word
                    </label>
                    <input 
                      type="text" 
                      value={config.wake_word}
                      onChange={(e) => setConfig(prev => ({ ...prev, wake_word: e.target.value }))}
                      className="w-full bg-cyber-darker border border-cyber-blue/20 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-cyber-blue/50"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-6 mt-6 border-t border-cyber-blue/20">
                <button 
                  onClick={() => handleSaveSettings(config)}
                  className="flex-1 bg-cyber-blue hover:bg-cyber-blue/80 text-cyber-darker font-bold py-2.5 px-4 rounded-lg text-xs tracking-wider transition-colors uppercase font-orbitron"
                >
                  Apply System Configuration
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
