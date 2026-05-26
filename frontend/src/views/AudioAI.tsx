import React, { useState, useEffect } from 'react';
import { Check, Copy, ArrowRight, AlertTriangle } from 'lucide-react';
import { callPython } from '../eel';

interface AudioAIProps {
  setStatus: (s: string) => void;
  setStatusLevel: (level: 'ready' | 'working' | 'error') => void;
  onImportScore: (notes: string, useTwoMallets: boolean, syncData: any, audioPath: string) => void;
}

export const AudioAI: React.FC<AudioAIProps> = ({
  setStatus,
  setStatusLevel,
  onImportScore,
}) => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string>('');
  const [twoMallets, setTwoMallets] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [calibrationActive, setCalibrationActive] = useState<boolean>(true);

  // Analysis progress states
  const [pct, setPct] = useState<number>(0);
  const [stage, setStage] = useState<string>('');
  const [detail, setDetail] = useState<string>('');
  const [polyInfo, setPolyInfo] = useState<{ is_polyphonic: boolean; poly_ratio: number; avg_peaks: number } | null>(null);

  // Results
  const [resultNotes, setResultNotes] = useState<string>('');
  const [syncData, setSyncData] = useState<any[]>([]);
  const [copied, setCopied] = useState<boolean>(false);
  const [transferred, setTransferred] = useState<boolean>(false);

  // Check calibration status on load
  useEffect(() => {
    const checkCalibration = async () => {
      try {
        const active = await callPython('check_calibration_api');
        setCalibrationActive(active);
      } catch (err) {
        console.error(err);
      }
    };
    checkCalibration();
  }, []);

  // Expose progress callback to Python
  useEffect(() => {
    const handleProgress = (progressPct: number, msg: string, poly: any, notesData: string, syncDataList: any[]) => {
      setPct(progressPct);
      setDetail(msg);

      // Determine stage name based on percentage
      const STAGES: { [key: number]: string } = {
        0: 'Initializing',
        5: 'Spectral Analysis',
        15: 'HPS Decomposition',
        25: 'Onset Mapping',
        40: 'Neural Decoding',
        80: 'Post-Processing',
        100: 'Neural Sync Complete',
      };

      let currentStage = 'Processing';
      Object.keys(STAGES)
        .map(Number)
        .sort((a, b) => a - b)
        .forEach((threshold) => {
          if (progressPct >= threshold) {
            currentStage = STAGES[threshold];
          }
        });

      setStage(currentStage);

      if (poly) {
        setPolyInfo(poly);
      }

      if (progressPct === 100) {
        setIsAnalyzing(false);
        setResultNotes(notesData);
        setSyncData(syncDataList);
        setStatus('●  Neural Sync Complete');
        setStatusLevel('ready');
      }
    };

    if (typeof window !== 'undefined' && window.eel) {
      window.eel.expose(handleProgress, 'js_transcribe_progress');
    }
  }, [setStatus, setStatusLevel]);

  const handleBrowse = async () => {
    try {
      const filePath = await callPython('select_audio_file_dialog');
      if (filePath) {
        setSelectedFile(filePath);
        setSelectedFileName(filePath.split(/[/\\]/).pop() || filePath);
        setResultNotes('');
        setPolyInfo(null);
        setPct(0);
        setStage('');
        setDetail('');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext === 'wav' || ext === 'mp3') {
        // Native Edge/Chrome webview stores absolute path in non-standard file.path property
        const path = (file as any).path || file.name;
        setSelectedFile(path);
        setSelectedFileName(file.name);
        setResultNotes('');
        setPolyInfo(null);
        setPct(0);
        setStage('');
        setDetail('');
      } else {
        alert('Please drop a WAV or MP3 audio file.');
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile || isAnalyzing) return;

    setIsAnalyzing(true);
    setResultNotes('');
    setPct(0);
    setStage('Initializing...');
    setDetail('Loading audio file...');
    setStatus('●  Processing Audio AI...');
    setStatusLevel('working');

    try {
      await callPython('start_audio_transcription', selectedFile, twoMallets);
    } catch (err: any) {
      setIsAnalyzing(false);
      setStatus('●  Transcription failed');
      setStatusLevel('error');
      setStage('Transcription Failed');
      setDetail(err.message || 'Unknown error');
    }
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(resultNotes);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePushToEditor = () => {
    if (!selectedFile) return;
    setTransferred(true);
    onImportScore(resultNotes, twoMallets, syncData, selectedFile);
    setTimeout(() => setTransferred(false), 2500);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto bg-[#121212] p-8 select-none">
      
      {/* HEADER SECTION */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="flex items-center space-x-3 mb-2">
          <span className="text-3xl">✨</span>
          <h1 className="text-white text-3xl font-extrabold tracking-tight">Audio AI Transcription</h1>
        </div>
        <p className="text-gray-400 text-sm">
          High-performance neural network analysis for transcribing traditional Cambodian Roneat Ek recordings.
        </p>
        <div className="h-[1px] bg-[#2e303a] w-full mt-6" />
      </div>

      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* CALIBRATION BANNER */}
        <div className={`p-4 rounded-xl border flex items-center space-x-3 ${
          calibrationActive 
            ? 'bg-green-500/5 border-green-500/20 text-green-400' 
            : 'bg-yellow-500/5 border-yellow-500/20 text-yellow-400'
        }`}>
          <span className="text-lg">{calibrationActive ? '✅' : '⚠️'}</span>
          <div className="text-xs font-semibold font-mono">
            {calibrationActive 
              ? 'Neural calibration active. Pitch fingerprints loaded for high-precision transcription.'
              : 'No custom calibration found. Using generic FFT pitch detection (Standard mode).'}
          </div>
        </div>

        {/* POLYPHONY WARNING BANNER */}
        {polyInfo && polyInfo.is_polyphonic && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 space-y-2 text-amber-400">
            <div className="flex items-center space-x-2 text-sm font-bold">
              <AlertTriangle className="w-4 h-4" />
              <span>Multi-instrument Audio Detected</span>
            </div>
            <div className="text-xs font-mono">
              Complexity: {(polyInfo.poly_ratio * 100).toFixed(0)}% density | Peaks: {polyInfo.avg_peaks.toFixed(1)} per frame
            </div>
            <p className="text-xs text-gray-400">
              Transcription works best with clean, solo Roneat recordings. Orchestral backings may cause ghost notes or timing shifts.
            </p>
          </div>
        )}

        {/* MAIN CONTROLS: DROP ZONE + SETTINGS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Drop Zone Card */}
          <div className="md:col-span-2 bg-[#1e1e1e] border border-[#2e303a] rounded-2xl p-4 flex flex-col justify-between min-h-[220px]">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className={`flex-1 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-6 transition duration-200 ${
                selectedFile 
                  ? 'border-[#d4af37]/60 bg-[#2a2d2e]/30' 
                  : 'border-[#2e303a] bg-[#1a1a1a] hover:border-gray-500'
              }`}
            >
              <span className="text-4xl mb-3">{selectedFile ? '🎵' : '📥'}</span>
              <h3 className="text-sm font-bold text-white mb-1">
                {selectedFile ? selectedFileName : 'Drop Audio File Here'}
              </h3>
              <p className="text-[10px] text-gray-500 text-center mb-4">
                Supports WAV, MP3 (44.1kHz / 48kHz mono or stereo)
              </p>
              
              <button
                onClick={handleBrowse}
                disabled={isAnalyzing}
                className="bg-transparent hover:bg-[#252526] text-[#d4af37] border border-[#d4af37] font-bold text-xs px-5 py-2 rounded-lg transition active:scale-98 cursor-pointer disabled:opacity-50"
              >
                Browse Files
              </button>
            </div>
          </div>

          {/* Algorithm Settings & Action */}
          <div className="flex flex-col justify-between space-y-4">
            <div className="bg-[#1e1e1e] border border-[#2e303a] rounded-2xl p-5 space-y-4 flex-1">
              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">
                Algorithm Settings
              </span>
              
              <div className="space-y-3">
                <label className="flex items-center justify-between cursor-pointer select-none">
                  <div className="flex flex-col">
                    <span className="text-xs text-white font-bold">Two Mallets Mode</span>
                    <span className="text-[9px] text-gray-500">Simulate left hand (+7 bars)</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={twoMallets}
                    onChange={(e) => setTwoMallets(e.target.checked)}
                    disabled={isAnalyzing}
                    className="rounded border-[#2e303a] bg-[#16171d] text-[#d4af37] focus:ring-0 cursor-pointer disabled:opacity-50"
                  />
                </label>
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={handleStartAnalysis}
              disabled={!selectedFile || isAnalyzing}
              className="w-full bg-[#d4af37] hover:bg-[#bfa032] text-black font-extrabold text-sm py-5 rounded-2xl transition duration-150 shadow-md active:scale-98 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed uppercase tracking-wider flex items-center justify-center space-x-2"
            >
              <span>{isAnalyzing ? 'Transcribing...' : 'Start AI Analysis'}</span>
            </button>
          </div>
        </div>

        {/* PROGRESS CARD */}
        {isAnalyzing && (
          <div className="bg-[#1e1e1e] border border-[#2e303a] rounded-2xl p-8 flex flex-col items-center justify-center space-y-4 animate-fade-in">
            {/* Spinning Loader */}
            <div className="relative w-20 h-20 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-gray-800" />
              <div className="absolute inset-0 rounded-full border-4 border-t-[#d4af37] animate-spin" />
              <span className="text-xs font-mono font-bold text-[#d4af37]">{pct}%</span>
            </div>

            <div className="text-center space-y-1">
              <h3 className="text-[#d4af37] text-md font-bold">{stage}</h3>
              <p className="text-xs text-gray-400 font-mono max-w-lg truncate">{detail}</p>
            </div>

            {/* Progress Bar */}
            <div className="w-full max-w-md h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                style={{ width: `${pct}%` }}
                className="h-full bg-[#d4af37] transition-all duration-300"
              />
            </div>
          </div>
        )}

        {/* RESULT CARD */}
        {resultNotes && !isAnalyzing && (
          <div className="bg-[#1e1e1e] border border-[#2e303a] rounded-2xl p-6 space-y-4 animate-fade-in">
            <div className="flex justify-between items-center pb-2 border-b border-[#2e303a]">
              <h3 className="text-white text-md font-bold">Transcription Result</h3>
              
              <div className="flex items-center space-x-2">
                {/* Copy Button */}
                <button
                  onClick={handleCopyToClipboard}
                  className="bg-transparent hover:bg-[#252526] text-[#d4af37] border border-[#d4af37]/30 hover:border-[#d4af37] font-semibold text-xs py-1.5 px-3 rounded flex items-center space-x-1.5 transition active:scale-98 cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            {/* Result text area */}
            <textarea
              readOnly
              value={resultNotes}
              className="w-full h-32 bg-[#16171d] border border-[#2e303a] rounded-xl p-4 text-md text-[#e0e0e0] font-mono leading-relaxed outline-none resize-none"
            />

            {/* Push to score editor button */}
            <button
              onClick={handlePushToEditor}
              className="w-full bg-[#3ab87a] hover:bg-[#2e9e66] text-[#0f1115] font-extrabold text-sm py-4 rounded-xl flex items-center justify-center space-x-2 transition active:scale-98 cursor-pointer shadow-md uppercase tracking-wider"
            >
              <span>{transferred ? '✓ Transferred successfully!' : 'Push to Score Editor'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

      </div>
    </div>
  );
};
