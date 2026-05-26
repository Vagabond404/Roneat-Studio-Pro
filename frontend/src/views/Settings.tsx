import React, { useState, useEffect } from 'react';
import { Sliders, Volume2, Sun, Moon, Save, CheckCircle, RotateCcw, FileAudio, Play, Activity } from 'lucide-react';
import { callPython, exposeToPython } from '../eel';

interface SettingsProps {
  setStatus: (s: string) => void;
  setStatusLevel: (level: 'ready' | 'working' | 'error') => void;
}

const applyTheme = (themeName: string) => {
  const root = document.documentElement;
  if (themeName === 'Light') {
    root.classList.add('light');
  } else if (themeName === 'Dark') {
    root.classList.remove('light');
  } else {
    const isSystemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (isSystemDark) {
      root.classList.remove('light');
    } else {
      root.classList.add('light');
    }
  }
};

export const Settings: React.FC<SettingsProps> = ({
  setStatus,
  setStatusLevel,
}) => {
  // App Preferences States
  const [audioMode, setAudioMode] = useState<string>('adsr');
  const [audioDevices, setAudioDevices] = useState<string[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('Default');
  const [theme, setTheme] = useState<string>('Dark');
  const [showToast, setShowToast] = useState<boolean>(false);
  const [samplesAvailable, setSamplesAvailable] = useState<boolean>(false);

  // Hz Tuning Matrix State
  const [hzPreset, setHzPreset] = useState<{ [key: string]: number }>({});

  // Calibration States
  const [singlePath, setSinglePath] = useState<string>('');
  const [twoPath, setTwoPath] = useState<string>('');
  const [calibrationProgress, setCalibrationProgress] = useState<number>(0);
  const [calibrationStatus, setCalibrationStatus] = useState<string>('Idle');

  // Load saved settings and tuning preset on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await callPython('get_settings');
        if (settings) {
          if (settings.theme) setTheme(settings.theme);
          if (settings.audio_device) setSelectedDevice(settings.audio_device);
          if (settings.audio_mode) setAudioMode(settings.audio_mode);
        }

        // Get available audio devices from backend
        const devices = await callPython('get_audio_devices_api');
        if (devices) {
          setAudioDevices(devices);
        }

        // Get active Hz Preset
        const preset = await callPython('get_hz_preset_api');
        if (preset) {
          setHzPreset(preset);
        }

        // Check if sample files are available in Roaming folder
        const samplesAvail = await callPython('get_samples_available_api');
        setSamplesAvailable(!!samplesAvail);

      } catch (err) {
        console.error('Error loading settings:', err);
      }
    };

    loadSettings();

    // Expose calibration progress callback to Python
    const handleCalibrationProgress = (pct: number, msg: string) => {
      setCalibrationProgress(pct);
      setCalibrationStatus(msg);
      if (pct === 100) {
        setStatus('●  Calibration completed successfully');
        setStatusLevel('ready');
        callPython('get_samples_available_api').then((avail) => setSamplesAvailable(!!avail));
      } else if (pct === -1) {
        setStatus(`●  Calibration failed: ${msg}`);
        setStatusLevel('error');
      } else {
        setStatus(`●  Calibrating: ${msg}`);
        setStatusLevel('working');
      }
    };

    exposeToPython('js_calibration_progress', handleCalibrationProgress);
  }, [setStatus, setStatusLevel]);

  // Live theme application
  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);
    applyTheme(newTheme);
  };

  // Reset Hz tuning preset to factory default
  const handleResetHzPreset = async () => {
    try {
      const defaultHz = await callPython('get_default_hz_api');
      if (defaultHz && Object.keys(defaultHz).length > 0) {
        setHzPreset(defaultHz);
        setStatus('●  Tuning reset to factory default values');
        setStatusLevel('ready');
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Select file dialog triggers
  const handleSelectSinglePath = async () => {
    try {
      const path = await callPython('select_audio_file_dialog');
      if (path) setSinglePath(path);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectTwoPath = async () => {
    try {
      const path = await callPython('select_audio_file_dialog');
      if (path) setTwoPath(path);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunCalibration = async () => {
    if (!singlePath && !twoPath) {
      alert('Please select at least one audio file to run calibration.');
      return;
    }
    setCalibrationProgress(0);
    setCalibrationStatus('Initializing spectral analysis...');
    setStatus('●  Calibrating...');
    setStatusLevel('working');
    try {
      await callPython('run_calibration_api', singlePath, twoPath);
    } catch (err: any) {
      setCalibrationProgress(-1);
      setCalibrationStatus(`Failed to launch calibration: ${err.message || err}`);
      setStatus('●  Calibration failed');
      setStatusLevel('error');
    }
  };

  // Save Settings & Preset changes
  const handleSave = async () => {
    setStatus('●  Saving system parameters...');
    setStatusLevel('working');

    try {
      // Validate frequencies
      for (const [key, val] of Object.entries(hzPreset)) {
        const num = parseFloat(val as any);
        if (isNaN(num) || num < 100 || num > 2000) {
          setStatus(`●  Invalid frequency on Bar ${key}: Must be between 100 and 2000 Hz.`);
          setStatusLevel('error');
          return;
        }
      }

      // 1. Save general preferences (language hardcoded to English)
      await callPython('save_settings_api', {
        language: 'en',
        theme,
        audio_device: selectedDevice,
        audio_mode: audioMode,
      });

      // 2. Save Hz tuning preset
      await callPython('save_hz_preset_api', hzPreset);

      setStatus('●  Settings applied successfully');
      setStatusLevel('ready');
      setShowToast(true);
      setTimeout(() => setShowToast(false), 2500);
    } catch (err: any) {
      setStatus(`●  Failed to save settings: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  // Helper to change single key frequency in tuning matrix
  const handleFrequencyChange = (key: string, value: string) => {
    const parsed = parseFloat(value);
    setHzPreset((prev) => ({
      ...prev,
      [key]: isNaN(parsed) ? 0 : parsed,
    }));
  };

  const cardClass = "bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 space-y-4 shadow-sm";
  const sectionHeader = "flex items-center space-x-2.5 pb-3 border-b border-[var(--border-color)]";
  const inputClass = "w-full bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-main)] font-bold rounded-lg px-3 py-2.5 outline-none focus:border-[#d4af37] transition duration-150 cursor-pointer";

  return (
    <div className="flex-1 h-full overflow-y-auto bg-[var(--bg-app)] p-8 select-none">

      {/* HEADER */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="flex items-center space-x-3 mb-2">
          <span className="text-3xl">⚙️</span>
          <h1 className="text-[var(--text-title)] text-3xl font-extrabold tracking-tight">System Settings</h1>
        </div>
        <p className="text-[var(--text-dim)] text-sm">
          Configure audio engine, pitch calibration, sound routing, and interface preferences.
        </p>
        <div className="h-[1px] bg-[var(--border-color)] w-full mt-6" />
      </div>

      <div className="max-w-4xl mx-auto space-y-6">

        {/* AUDIO ENGINE CARD */}
        <div className={cardClass}>
          <div className={sectionHeader}>
            <Volume2 className="w-5 h-5 text-[#d4af37]" />
            <h3 className="text-[var(--text-title)] text-sm font-bold uppercase tracking-wider">Audio Engine</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-xs text-[var(--text-main)] block mb-2 font-bold">Synthesis Mode</label>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setAudioMode('adsr')}
                  className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-bold border transition duration-150 cursor-pointer ${
                    audioMode === 'adsr'
                      ? 'bg-[#d4af37] text-black border-[#d4af37]'
                      : 'bg-[var(--bg-input)] text-[var(--text-main)] border-[var(--border-color)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  ADSR Synthesis
                </button>
                <button
                  type="button"
                  onClick={() => samplesAvailable && setAudioMode('samples')}
                  disabled={!samplesAvailable}
                  className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-bold border transition duration-150 cursor-pointer ${
                    audioMode === 'samples'
                      ? 'bg-[#d4af37] text-black border-[#d4af37]'
                      : !samplesAvailable
                      ? 'bg-[var(--bg-input)] text-[var(--text-dim)] border-[var(--border-color)] cursor-not-allowed opacity-50'
                      : 'bg-[var(--bg-input)] text-[var(--text-main)] border-[var(--border-color)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  Real Samples
                </button>
              </div>
              {!samplesAvailable && (
                <span className="text-[9px] text-amber-500 font-mono mt-1.5 block">
                  ⚠️ Complete mallet fingerprint calibration below to unlock Real Samples mode.
                </span>
              )}
            </div>

            <div>
              <label className="text-xs text-[var(--text-main)] block mb-2 font-bold">Output Sound Device</label>
              <select
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                className={inputClass}
              >
                <option value="Default">System Default Output</option>
                {audioDevices.map((dev) => (
                  <option key={dev} value={dev}>{dev}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* HZ TUNING MATRIX CARD */}
        <div className={cardClass}>
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <div className="flex items-center space-x-2.5">
              <Sliders className="w-5 h-5 text-[#d4af37]" />
              <h3 className="text-[var(--text-title)] text-sm font-bold uppercase tracking-wider">Note Calibration Matrix (Hz)</h3>
            </div>
            <button
              onClick={handleResetHzPreset}
              className="text-xs text-[var(--text-main)] hover:text-[#d4af37] flex items-center space-x-1.5 font-bold transition duration-150 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset to Default</span>
            </button>
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-7 gap-3">
            {Array.from({ length: 21 }).map((_, i) => {
              const barId = (i + 1).toString();
              const frequency = hzPreset[barId] || 0;
              return (
                <div key={barId} className="bg-[var(--bg-input)] p-2.5 rounded-lg border border-[var(--border-color)] flex flex-col items-center shadow-inner">
                  <span className="text-[9px] text-[var(--text-dim)] font-extrabold font-mono tracking-tighter mb-1.5">BAR {barId}</span>
                  <input
                    type="number"
                    value={frequency || ''}
                    onChange={(e) => handleFrequencyChange(barId, e.target.value)}
                    min="100"
                    max="2000"
                    step="0.1"
                    className="w-full bg-transparent border-0 text-center text-xs font-mono font-bold text-[#d4af37] outline-none"
                    placeholder="---"
                  />
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-[var(--text-dim)] leading-relaxed">
            Standard Cambodian Roneat Ek frequency ranges between 177 Hz (bar 21, lowest) and 1308 Hz (bar 1, highest). Adjust to recalibrate pitch detection.
          </p>
        </div>

        {/* CALIBRATION CARD */}
        <div className={cardClass}>
          <div className={sectionHeader}>
            <Activity className="w-5 h-5 text-[#d4af37]" />
            <h3 className="text-[var(--text-title)] text-sm font-bold uppercase tracking-wider">Instrument Fingerprint Calibration</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-[var(--text-main)] block font-bold">Single Mallet Recording (.mp3 / .wav)</label>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleSelectSinglePath}
                    className="bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] text-[var(--text-main)] border border-[var(--border-color)] font-bold text-xs py-2 px-4 rounded-lg flex items-center space-x-2 transition duration-150 cursor-pointer"
                  >
                    <FileAudio className="w-4 h-4 text-[#d4af37]" />
                    <span>Browse...</span>
                  </button>
                  <span className="text-xs text-[var(--text-dim)] truncate flex-1 font-mono">
                    {singlePath ? singlePath.split(/[/\\]/).pop() : 'No file selected'}
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-[var(--text-main)] block font-bold">Two Mallets Recording (.mp3 / .wav)</label>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleSelectTwoPath}
                    className="bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] text-[var(--text-main)] border border-[var(--border-color)] font-bold text-xs py-2 px-4 rounded-lg flex items-center space-x-2 transition duration-150 cursor-pointer"
                  >
                    <FileAudio className="w-4 h-4 text-[#d4af37]" />
                    <span>Browse...</span>
                  </button>
                  <span className="text-xs text-[var(--text-dim)] truncate flex-1 font-mono">
                    {twoPath ? twoPath.split(/[/\\]/).pop() : 'No file selected'}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-[var(--bg-input)] p-4 rounded-xl border border-[var(--border-color)] flex flex-col justify-between">
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-[#d4af37] uppercase tracking-wider block">Calibration Status</span>
                <span className="text-xs text-[var(--text-main)] font-mono block leading-relaxed">{calibrationStatus}</span>
              </div>

              {calibrationProgress > 0 && (
                <div className="space-y-1.5 mt-4">
                  <div className="flex justify-between items-center text-[10px] text-[var(--text-dim)] font-mono">
                    <span>Progress</span>
                    <span>{calibrationProgress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[var(--bg-card)] rounded-full overflow-hidden">
                    <div
                      style={{ width: `${calibrationProgress}%` }}
                      className="h-full bg-[#d4af37] transition-all duration-300"
                    />
                  </div>
                </div>
              )}

              <button
                onClick={handleRunCalibration}
                disabled={!singlePath && !twoPath}
                className={`w-full py-2.5 px-4 rounded-lg font-bold text-xs flex items-center justify-center space-x-2 shadow transition duration-150 mt-4 cursor-pointer ${
                  (!singlePath && !twoPath)
                    ? 'bg-[var(--bg-card)] text-[var(--text-dim)] border border-[var(--border-color)] cursor-not-allowed opacity-50'
                    : 'bg-[#d4af37] hover:bg-[#c49f2d] text-black'
                }`}
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Analyze & Build Fingerprints</span>
              </button>
            </div>
          </div>
        </div>

        {/* PREFERENCES CARD — Theme Only */}
        <div className={cardClass}>
          <div className={sectionHeader}>
            {theme === 'Light' ? (
              <Sun className="w-5 h-5 text-[#d4af37]" />
            ) : (
              <Moon className="w-5 h-5 text-[#d4af37]" />
            )}
            <h3 className="text-[var(--text-title)] text-sm font-bold uppercase tracking-wider">Interface Preferences</h3>
          </div>

          <div>
            <label className="text-xs text-[var(--text-main)] block mb-3 font-bold">Theme Mode</label>
            <div className="flex space-x-3">
              {['Dark', 'Light', 'System'].map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => handleThemeChange(opt)}
                  className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-bold border transition duration-150 cursor-pointer flex items-center justify-center space-x-2 ${
                    theme === opt
                      ? 'bg-[#d4af37] text-black border-[#d4af37]'
                      : 'bg-[var(--bg-input)] text-[var(--text-main)] border-[var(--border-color)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  <span>{opt === 'Dark' ? '🌙' : opt === 'Light' ? '☀️' : '🖥️'}</span>
                  <span>{opt}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* SAVE ACTION */}
        <div className="flex items-center justify-between pt-4 pb-12">
          {showToast ? (
            <div className="flex items-center text-xs text-green-500 font-mono font-bold animate-pulse">
              <CheckCircle className="w-4 h-4 mr-2" />
              <span>Settings applied successfully!</span>
            </div>
          ) : (
            <div />
          )}

          <button
            onClick={handleSave}
            className="bg-[#d4af37] hover:bg-[#c49f2d] text-black font-extrabold text-xs py-3 px-8 rounded-lg flex items-center justify-center space-x-2 transition duration-150 shadow-md active:scale-95 cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Apply & Save Settings</span>
          </button>
        </div>

      </div>
    </div>
  );
};
