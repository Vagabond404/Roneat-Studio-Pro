import React, { useState, useEffect } from 'react';
import { Play, Square, FileText, Video, Sliders, CheckCircle } from 'lucide-react';
import { RoneatKeyboard } from '../components/RoneatKeyboard';
import { ScoreGrid } from '../components/ScoreGrid';
import { callPython } from '../eel';

interface ScoreEditorProps {
  projectData: any;
  setProjectData: React.Dispatch<React.SetStateAction<any>>;
  activeNote: number | null;
  setActiveNote: (note: number | null) => void;
  activeLeftNote: number | null;
  setActiveLeftNote: (note: number | null) => void;
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
  status: string;
  setStatus: (s: string) => void;
  setStatusLevel: (level: 'ready' | 'working' | 'error') => void;
}

export const ScoreEditor: React.FC<ScoreEditorProps> = ({
  projectData,
  setProjectData,
  activeNote,
  setActiveNote,
  activeLeftNote,
  setActiveLeftNote,
  isPlaying,
  setIsPlaying,
  setStatus,
  setStatusLevel,
}) => {
  const [activeView, setActiveView] = useState<'table' | 'roneat2d'>('table');
  const [roneatMode, setRoneatMode] = useState<'playback' | 'edit' | 'jam'>('playback');
  const [twoMallets, setTwoMallets] = useState<boolean>(true);
  const [tremoloHold, setTremoloHold] = useState<number>(0.4);

  // Metronome and feedback states
  const [metroBeat, setMetroBeat] = useState<boolean>(false);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [videoProgress, setVideoProgress] = useState<number>(0);
  const [videoStatus, setVideoStatus] = useState<string>('');

  // Extract variables from projectData with sensible defaults
  const {
    title = '',
    author = 'Anonymous',
    notes = '',
    bpm = '170',
    grid = '8 Columns (Large)',
    measure = "Manual (using '/')",
    font_size = 14,
    accent = '#c8a96e',
    left_hand = true,
    show_nums = true,
    hits_sec = '10',
    viewMode = 'Numeric',
  } = projectData;

  const updateField = (key: string, value: any) => {
    setProjectData((prev: any) => {
      const updated = { ...prev, [key]: value };
      callPython('update_project_data_field', key, value);
      return updated;
    });
  };

  // Convert columns label to integer
  const getGridColumnsCount = () => {
    const num = parseInt(grid.split(' ')[0]);
    return isNaN(num) ? 16 : num;
  };

  // Playback Control
  const handlePlay = async () => {
    if (isPlaying) return;
    setIsPlaying(true);
    setStatus('●  Playing score...');
    setStatusLevel('working');
    try {
      await callPython('play_score_api', notes, bpm, left_hand, hits_sec);
    } catch (err) {
      console.error(err);
      setStatus('●  Playback failed');
      setStatusLevel('error');
      setIsPlaying(false);
    }
  };

  const handleStop = async () => {
    setIsPlaying(false);
    setStatus('●  Stopped');
    setStatusLevel('ready');
    try {
      await callPython('stop_score_api');
    } catch (err) {
      console.error(err);
    }
  };

  // Keyboard press triggers audio synthesis or appends notes
  const handleNoteTriggered = async (note: number, repeat?: number) => {
    try {
      await callPython('trigger_jam_note', note, twoMallets);
    } catch (err) {
      console.error(err);
    }

    if (roneatMode === 'edit') {
      let token = note.toString();
      let feedback = `Append: note ${note}`;

      if (repeat && repeat > 1) {
        token = `${note}#${repeat}`;
        feedback = `Append: note ${note} (tremolo x${repeat})`;
      }

      setFeedbackText(feedback);
      setTimeout(() => setFeedbackText(''), 1500);

      const sep = notes.trim() ? ' ' : '';
      updateField('notes', notes.trim() + sep + token);
    }
  };

  // Play a note when its grid cell is clicked in the score sheet preview
  const handleBeatClick = async (index: number) => {
    const tokens = notes.replace(/\n/g, ' ').split(/\s+/).filter(Boolean);
    const token = tokens[index];
    if (token) {
      const TOK_RE = /^(\d+)(#(\d+))?$/;
      const LEFT_RIGHT_RE = /^\((\d+)\)(\d+)(#(\d+))?$/;

      let bar: number | null = null;

      const m_lr = token.match(LEFT_RIGHT_RE);
      if (m_lr) {
        bar = parseInt(m_lr[2]);
      } else {
        const m = token.match(TOK_RE);
        if (m) bar = parseInt(m[1]);
      }

      if (bar !== null) {
        try {
          await callPython('trigger_jam_note', bar, twoMallets);
        } catch (err) {
          console.error(err);
        }
      }
    }
  };

  const handleExportPDF = async () => {
    setStatus('●  Generating PDF...');
    setStatusLevel('working');
    try {
      const path = await callPython('export_pdf_api');
      if (path) {
        setStatus(`●  PDF Exported: ${path}`);
        setStatusLevel('ready');
      } else {
        setStatus('●  PDF Export Cancelled');
        setStatusLevel('ready');
      }
    } catch (err: any) {
      setStatus(`●  PDF Export Error: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  const handleExportMP4 = async () => {
    setStatus('●  Rendering Video (MP4)...');
    setStatusLevel('working');
    setVideoProgress(0);
    setVideoStatus('Initializing renderer...');
    try {
      const success = await callPython('export_mp4_api');
      if (success) {
        setStatus('●  Video Exported Successfully');
        setStatusLevel('ready');
        setVideoStatus('Done!');
        setVideoProgress(100);
      } else {
        setStatus('●  Video Export Cancelled');
        setStatusLevel('ready');
        setVideoStatus('');
      }
    } catch (err: any) {
      setStatus(`●  Video Export Error: ${err.message || err}`);
      setStatusLevel('error');
      setVideoStatus('Failed');
    }
  };

  // Listen to metronome and active beat callbacks from python
  useEffect(() => {
    const handleMetronomeTick = (beatOn: boolean) => {
      setMetroBeat(beatOn);
    };

    const handleActiveBeatHighlight = (beatIndex: number | null, leftBeatIndex: number | null) => {
      if (beatIndex === null) {
        setActiveNote(null);
        setActiveLeftNote(null);
        setIsPlaying(false);
        setStatus('●  Ready');
        setStatusLevel('ready');
      } else {
        setActiveNote(beatIndex);
        setActiveLeftNote(leftBeatIndex);
      }
    };

    const handleVideoExportProgress = (progress: number, label: string) => {
      setVideoProgress(progress);
      setVideoStatus(label);
    };

    if (typeof window !== 'undefined' && window.eel) {
      window.eel.expose(handleMetronomeTick, 'js_metronome_tick');
      window.eel.expose(handleActiveBeatHighlight, 'js_active_beat_highlight');
      window.eel.expose(handleVideoExportProgress, 'js_video_export_progress');
    }
  }, [setActiveNote, setActiveLeftNote, setIsPlaying, setStatus, setStatusLevel]);

  const inputClass = "w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded px-3 py-1.5 text-xs text-[var(--text-main)] outline-none focus:border-[#d4af37] transition duration-150";
  const selectClass = "w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded px-2.5 py-1.5 text-xs text-[var(--text-main)] outline-none focus:border-[#d4af37] cursor-pointer";
  const cardClass = "bg-[var(--bg-card)] rounded-lg p-4 border border-[var(--border-color)] space-y-3";

  return (
    <div className="flex h-full w-full overflow-hidden bg-[var(--bg-app)] text-[var(--text-main)]">

      {/* ═══════════════════════════════════════════════════════
          LEFT PANEL — Controls, Metadata, Notes, Export
          ═══════════════════════════════════════════════════════ */}
      <div className="w-80 border-r border-[var(--border-sidebar)] h-full flex flex-col bg-[var(--bg-panel)] overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* ── Project Information ── */}
          <div className={cardClass}>
            <div className="text-[10px] font-extrabold text-[var(--text-dim)] uppercase tracking-widest">Project Information</div>
            <div className="space-y-2">
              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1">Score Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => updateField('title', e.target.value)}
                  placeholder="Enter score title..."
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1">Author / Composer</label>
                <input
                  type="text"
                  value={author}
                  onChange={(e) => updateField('author', e.target.value)}
                  placeholder="Composer name..."
                  className={inputClass}
                />
              </div>
            </div>
          </div>

          {/* ── Display Settings ── */}
          <div className={cardClass}>
            <div className="text-[10px] font-extrabold text-[var(--text-dim)] uppercase tracking-widest flex items-center">
              <Sliders className="w-3 h-3 mr-1.5 text-[#d4af37]" />
              Display Settings
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1">Measure Style</label>
                <select value={measure} onChange={(e) => updateField('measure', e.target.value)} className={selectClass}>
                  <option value="4 beats">4 beats</option>
                  <option value="8 beats">8 beats</option>
                  <option value="Manual (using '/')">Manual (using '/')</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1">Grid Columns</label>
                <select value={grid} onChange={(e) => updateField('grid', e.target.value)} className={selectClass}>
                  <option value="8 Columns (Large)">8 Columns (Large)</option>
                  <option value="12 Columns">12 Columns</option>
                  <option value="16 Columns (Medium)">16 Columns (Medium)</option>
                  <option value="20 Columns">20 Columns</option>
                  <option value="24 Columns (Small)">24 Columns (Small)</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-[10px] text-[var(--text-dim)]">Note Font Size</label>
                  <span className="text-[10px] font-bold text-[#d4af37]">{font_size}px</span>
                </div>
                <input
                  type="range" min="8" max="22" step="1"
                  value={font_size}
                  onChange={(e) => updateField('font_size', parseInt(e.target.value))}
                  className="w-full h-1.5 bg-[var(--bg-input)] rounded-lg appearance-none cursor-pointer accent-[#d4af37]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1.5">Accent Color</label>
                <div className="flex items-center space-x-2">
                  {['#c8a96e', '#e85d4a', '#3d8ec9', '#3ab87a', '#a78bfa'].map((hex) => (
                    <button
                      key={hex}
                      onClick={() => updateField('accent', hex)}
                      style={{ backgroundColor: hex }}
                      className={`w-6 h-6 rounded-md transition duration-150 focus:outline-none cursor-pointer border ${
                        accent === hex ? 'border-white scale-110 shadow-md' : 'border-transparent hover:scale-105'
                      }`}
                    />
                  ))}
                </div>
              </div>

              <div className="pt-1 space-y-2">
                <label className="flex items-center justify-between cursor-pointer select-none">
                  <span className="text-xs text-[var(--text-main)]">Show Left Hand (+7 bars)</span>
                  <input
                    type="checkbox"
                    checked={left_hand}
                    onChange={(e) => updateField('left_hand', e.target.checked)}
                    className="rounded border-[var(--border-color)] bg-[var(--bg-input)] text-[#d4af37] focus:ring-0 cursor-pointer"
                  />
                </label>
                <label className="flex items-center justify-between cursor-pointer select-none">
                  <span className="text-xs text-[var(--text-main)]">Show Bar Numbers</span>
                  <input
                    type="checkbox"
                    checked={show_nums}
                    onChange={(e) => updateField('show_nums', e.target.checked)}
                    className="rounded border-[var(--border-color)] bg-[var(--bg-input)] text-[#d4af37] focus:ring-0 cursor-pointer"
                  />
                </label>
              </div>
            </div>
          </div>

          {/* ── Audio Transport ── */}
          <div className={cardClass}>
            <div className="text-[10px] font-extrabold text-[var(--text-dim)] uppercase tracking-widest">Playback</div>
            <div className="flex items-center space-x-3">
              {isPlaying ? (
                <button
                  onClick={handleStop}
                  className="bg-red-600 hover:bg-red-500 text-white font-bold p-2.5 rounded-lg flex items-center justify-center transition shadow active:scale-95 cursor-pointer"
                >
                  <Square className="w-4 h-4 fill-current" />
                </button>
              ) : (
                <button
                  onClick={handlePlay}
                  className="bg-[#d4af37] hover:bg-[#c49f2d] text-black font-bold p-2.5 rounded-lg flex items-center justify-center transition shadow active:scale-95 cursor-pointer"
                >
                  <Play className="w-4 h-4 fill-current" />
                </button>
              )}
              {/* Metronome Beat */}
              <div className="flex items-center space-x-2 pl-2 border-l border-[var(--border-color)]">
                <div className={`w-3.5 h-3.5 rounded-full border border-[var(--border-color)] transition-colors duration-75 ${metroBeat ? 'bg-[#d4af37] shadow-[0_0_8px_#d4af37]' : 'bg-[var(--bg-input)]'}`} />
                <span className="text-[10px] text-[var(--text-dim)] font-mono tracking-wider">METRO</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1">BPM Tempo</label>
                <input
                  type="number" min="20" max="400"
                  value={bpm}
                  onChange={(e) => updateField('bpm', e.target.value)}
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded px-2 py-1 text-center text-xs text-[var(--text-main)] font-bold outline-none focus:border-[#d4af37]"
                />
              </div>
              <div>
                <label className="text-[10px] text-[var(--text-dim)] block mb-1">Tremolo (hits/s)</label>
                <input
                  type="number" min="2" max="32"
                  value={hits_sec}
                  onChange={(e) => updateField('hits_sec', e.target.value)}
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded px-2 py-1 text-center text-xs text-[var(--text-main)] font-bold outline-none focus:border-[#d4af37]"
                />
              </div>
            </div>
          </div>

          {/* ── Score Text Editor ── */}
          <div className={cardClass}>
            <div className="text-[10px] font-extrabold text-[var(--text-dim)] uppercase tracking-widest">Score Text Editor</div>
            <p className="text-[10px] text-[var(--text-dim)]">Space-separated note numbers. Use '/' for barline, '-' for rest, '#N' for tremolo.</p>
            <textarea
              value={notes}
              onChange={(e) => updateField('notes', e.target.value)}
              placeholder="e.g. 1 1 2 1 4 3 / 1 1 2 1 5 4 / 1 1 8 6 4 3 2 / ..."
              rows={6}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg p-3 text-sm text-[var(--text-main)] font-mono leading-relaxed outline-none focus:border-[#d4af37] resize-none"
            />
          </div>

          {/* ── Export ── */}
          <div className={cardClass}>
            <div className="text-[10px] font-extrabold text-[var(--text-dim)] uppercase tracking-widest">Export Studio</div>
            <div className="space-y-2">
              <button
                onClick={handleExportPDF}
                className="w-full bg-[#d4af37] hover:bg-[#c49f2d] text-black font-bold text-xs py-2.5 px-4 rounded flex items-center justify-center space-x-2 transition duration-150 active:scale-95 cursor-pointer"
              >
                <FileText className="w-4 h-4" />
                <span>Export to PDF</span>
              </button>
              <button
                onClick={handleExportMP4}
                className="w-full bg-transparent hover:bg-[var(--bg-hover)] text-[#d4af37] border border-[#d4af37]/50 hover:border-[#d4af37] font-semibold text-xs py-2.5 px-4 rounded flex items-center justify-center space-x-2 transition duration-150 active:scale-95 cursor-pointer"
              >
                <Video className="w-4 h-4" />
                <span>Export 2D Video (MP4)</span>
              </button>

              {videoStatus && (
                <div className="bg-[var(--bg-input)] border border-[var(--border-color)] rounded p-2.5 space-y-1.5 mt-1">
                  <div className="flex justify-between items-center text-[10px] text-[var(--text-dim)]">
                    <span className="truncate max-w-[130px] font-mono">{videoStatus}</span>
                    <span className="font-bold text-[#d4af37]">{videoProgress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[var(--bg-card)] rounded-full overflow-hidden">
                    <div
                      style={{ width: `${videoProgress}%` }}
                      className="h-full bg-[#d4af37] transition-all duration-300"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          RIGHT PANEL — Score Preview & Roneat Keyboard
          ═══════════════════════════════════════════════════════ */}
      <div className="flex-1 h-full flex flex-col overflow-hidden">

        {/* View & Notation Switcher Header */}
        <div className="flex justify-between items-center px-5 py-3 bg-[var(--bg-panel)] border-b border-[var(--border-color)] flex-shrink-0">
          <div className="flex items-center space-x-3">
            <h2 className="text-[#d4af37] font-bold text-base">Score Preview</h2>
            <div className="bg-[var(--bg-card)] p-0.5 rounded-md flex border border-[var(--border-color)]">
              <button
                onClick={() => setActiveView('table')}
                className={`text-xs px-3 py-1.5 rounded font-medium transition cursor-pointer ${
                  activeView === 'table' ? 'bg-[#d4af37] text-black font-bold' : 'text-[var(--text-dim)] hover:text-[var(--text-main)]'
                }`}
              >
                Table View
              </button>
              <button
                onClick={() => setActiveView('roneat2d')}
                className={`text-xs px-3 py-1.5 rounded font-medium transition cursor-pointer ${
                  activeView === 'roneat2d' ? 'bg-[#d4af37] text-black font-bold' : 'text-[var(--text-dim)] hover:text-[var(--text-main)]'
                }`}
              >
                2D Roneat
              </button>
            </div>
          </div>

          {/* Notation Mode Segmented Picker */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5">
              <div className={`w-2 h-2 rounded-full transition-colors duration-75 ${metroBeat ? 'bg-[#d4af37] shadow-[0_0_6px_#d4af37]' : 'bg-[var(--bg-card)] border border-[var(--border-color)]'}`} />
              {isPlaying ? (
                <span className="text-[10px] text-yellow-400 font-mono font-bold">● PLAYING</span>
              ) : (
                <span className="text-[10px] text-[var(--text-dim)] font-mono">READY</span>
              )}
            </div>
            <div className="bg-[var(--bg-card)] p-0.5 rounded-md flex border border-[var(--border-color)]">
              {['Numeric', 'Letters', 'Syllabic'].map((modeOpt) => (
                <button
                  key={modeOpt}
                  onClick={() => updateField('viewMode', modeOpt)}
                  className={`text-xs px-3 py-1.5 rounded font-bold transition cursor-pointer ${
                    viewMode === modeOpt ? 'bg-[#d4af37] text-black' : 'text-[var(--text-dim)] hover:text-[var(--text-main)]'
                  }`}
                >
                  {modeOpt}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Preview Container — fills all remaining height with its own scroll */}
        <div className="flex-1 overflow-hidden min-h-0">
          {activeView === 'table' ? (
            <ScoreGrid
              notesText={notes}
              viewMode={viewMode}
              gridColumns={getGridColumnsCount()}
              fontSize={font_size}
              leftHand={left_hand}
              activeBeatIndex={activeNote}
              title={title}
              author={author}
              onBeatClick={handleBeatClick}
            />
          ) : (
            <div className="h-full flex flex-col overflow-hidden">
              {/* Roneat Mode Toolbar */}
              <div className="bg-[var(--bg-panel)] border-b border-[var(--border-color)] px-4 py-2.5 flex justify-between items-center text-xs flex-shrink-0">
                <div className="flex items-center space-x-3">
                  <span className="text-[var(--text-dim)] font-bold uppercase tracking-wider text-[10px]">Mode:</span>
                  <div className="bg-[var(--bg-card)] p-0.5 rounded flex border border-[var(--border-color)]">
                    {(['playback', 'edit', 'jam'] as const).map((mk) => (
                      <button
                        key={mk}
                        onClick={() => setRoneatMode(mk)}
                        className={`px-3 py-1 rounded font-bold capitalize transition cursor-pointer text-xs ${
                          roneatMode === mk ? 'bg-[#d4af37] text-black' : 'text-[var(--text-dim)] hover:text-[var(--text-main)]'
                        }`}
                      >
                        {mk}
                      </button>
                    ))}
                  </div>
                  <span className="text-[var(--text-dim)] font-mono italic text-[10px]">
                    {roneatMode === 'playback' && 'Keys highlight during score playback'}
                    {roneatMode === 'edit' && 'Click keys to write note. Hold for tremolo.'}
                    {roneatMode === 'jam' && 'Jam freely! Click keys to hear sounds instantly.'}
                  </span>
                </div>

                {roneatMode !== 'playback' && (
                  <div className="flex items-center space-x-4 border-l border-[var(--border-color)] pl-4">
                    <label className="flex items-center space-x-2 cursor-pointer select-none">
                      <span className="text-[var(--text-dim)] text-xs">Two Mallets</span>
                      <input
                        type="checkbox"
                        checked={twoMallets}
                        onChange={(e) => setTwoMallets(e.target.checked)}
                        className="rounded border-[var(--border-color)] bg-[var(--bg-input)] text-[#d4af37] focus:ring-0 cursor-pointer"
                      />
                    </label>

                    {roneatMode === 'edit' && (
                      <div className="flex items-center space-x-2 border-l border-[var(--border-color)] pl-4">
                        <span className="text-[var(--text-dim)] text-xs">Tremolo Hold:</span>
                        <input
                          type="range" min="0.2" max="1.5" step="0.1"
                          value={tremoloHold}
                          onChange={(e) => setTremoloHold(parseFloat(e.target.value))}
                          className="h-1 bg-[var(--bg-card)] rounded appearance-none cursor-pointer accent-[#d4af37] w-20"
                        />
                        <span className="text-[#d4af37] font-mono text-xs w-8">{tremoloHold.toFixed(1)}s</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Roneat 2D Keyboard */}
              <div className="flex-1 min-h-0 overflow-hidden p-4">
                <RoneatKeyboard
                  mode={roneatMode}
                  twoMallets={roneatMode === 'playback' ? left_hand : twoMallets}
                  activeNote={activeNote}
                  activeLeftNote={activeLeftNote}
                  accentColor={accent}
                  onNoteTriggered={handleNoteTriggered}
                  showNumbers={show_nums}
                  viewMode={viewMode}
                />
              </div>

              {/* Feedback Toast */}
              {feedbackText && (
                <div className="bg-[var(--bg-card)] border border-[#d4af37]/30 text-[#d4af37] mx-4 mb-4 rounded px-4 py-2 text-center text-xs font-mono font-bold shadow-md flex-shrink-0">
                  {feedbackText}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Audio Engine Status Bar */}
        <div className="bg-[var(--bg-panel)] border-t border-[var(--border-color)] px-5 py-1.5 flex items-center justify-end flex-shrink-0">
          <div className="flex items-center text-[10px] text-green-500 font-mono bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded">
            <CheckCircle className="w-3 h-3 mr-1.5" />
            <span>Audio Engine Loaded</span>
          </div>
        </div>

      </div>
    </div>
  );
};
