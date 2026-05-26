import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ScoreEditor } from './views/ScoreEditor';
import { AudioAI } from './views/AudioAI';
import { Settings } from './views/Settings';
import { Plugins } from './views/Plugins';
import { callPython, exposeToPython } from './eel';

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

function App() {
  const [activeTab, setActiveTab] = useState<string>('editor');
  const [status, setStatus] = useState<string>('●  Ready');
  const [statusLevel, setStatusLevel] = useState<'ready' | 'working' | 'error'>('ready');
  
  // Instrument and Plugin states
  const [availableInstruments, setAvailableInstruments] = useState<[string, string][]>([]);
  const [activeInstrument, setActiveInstrument] = useState<string>('roneat_ek');
  const [pluginTabs, setPluginTabs] = useState<{ tab_id: string; label: string; icon: string }[]>([]);
  
  // Active playing highlights (metronome / note highlights)
  const [activeNote, setActiveNote] = useState<number | null>(null);
  const [activeLeftNote, setActiveLeftNote] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Score editor project state
  const [projectData, setProjectData] = useState<any>({
    title: 'Happy Birthday',
    author: 'Traditional',
    notes: '1 1 2 1 4 3 / 1 1 2 1 5 4 / 1 1 8 6 4 3 2 / 10 10 9 6 7 6',
    bpm: '170',
    grid: '8 Columns (Large)',
    measure: "Manual (using '/')",
    font_size: 14,
    accent: '#c8a96e',
    left_hand: true,
    show_nums: true,
    hits_sec: '10',
    viewMode: 'Numeric',
    instrument_id: 'roneat_ek',
  });

  // Load project settings and configuration from Python on startup
  const loadWorkspace = async () => {
    try {
      // 1. Get current project state
      const proj = await callPython('get_project_data_api');
      if (proj) {
        setProjectData(proj);
        if (proj.instrument_id) {
          setActiveInstrument(proj.instrument_id);
        }
      }

      // 2. Get available instrument plugins
      const instruments = await callPython<[string, string][]>('get_available_instruments_api');
      if (instruments) {
        setAvailableInstruments(instruments);
      }

      // 3. Get plugin custom tabs
      const tabs = await callPython<any[]>('get_plugin_custom_tabs_api');
      if (tabs) {
        setPluginTabs(tabs);
      }

      // 4. Get and apply system settings theme
      const settings = await callPython('get_settings');
      if (settings && settings.theme) {
        applyTheme(settings.theme);
      }
    } catch (err) {
      console.error('Error loading Eel workspace:', err);
    }
  };

  useEffect(() => {
    loadWorkspace();

    // Expose dynamic project loading function to Python so it can be called from load dialog
    const handleLoadProjectFromPython = (data: any, filepath: string) => {
      setProjectData(data);
      if (data.instrument_id) {
        setActiveInstrument(data.instrument_id);
      }
      setStatus(`●  Loaded: ${filepath.split(/[/\\]/).pop() || filepath}`);
      setStatusLevel('ready');
      setActiveTab('editor');
    };

    exposeToPython('js_load_project_data', handleLoadProjectFromPython);

    const handleShowToast = (message: string, level: string, duration?: number) => {
      setStatus(`●  ${message}`);
      setStatusLevel(level === 'error' ? 'error' : level === 'working' ? 'working' : 'ready');
      if (duration && duration > 0) {
        setTimeout(() => {
          setStatus('●  Ready');
          setStatusLevel('ready');
        }, duration);
      }
    };
    exposeToPython('js_show_toast', handleShowToast);
  }, []);

  const handleSaveProject = async () => {
    setStatus('●  Saving project...');
    setStatusLevel('working');
    try {
      const savedPath = await callPython('save_project_dialog_api');
      if (savedPath) {
        setStatus(`●  Saved: ${savedPath.split(/[/\\]/).pop()}`);
        setStatusLevel('ready');
      } else {
        setStatus('●  Save cancelled');
        setStatusLevel('ready');
      }
    } catch (err: any) {
      setStatus(`●  Save failed: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  const handleLoadProject = async () => {
    setStatus('●  Loading project...');
    setStatusLevel('working');
    try {
      await callPython('load_project_dialog_api');
    } catch (err: any) {
      setStatus(`●  Load failed: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  const handleInstrumentChange = async (id: string) => {
    setActiveInstrument(id);
    setStatus(`●  Switching instrument to ${id}...`);
    setStatusLevel('working');
    try {
      const success = await callPython('change_instrument_api', id);
      if (success) {
        setStatus(`●  Active Instrument: ${id}`);
        setStatusLevel('ready');
        // Update projectData
        setProjectData((prev: any) => ({ ...prev, instrument_id: id }));
      }
    } catch (err: any) {
      setStatus(`●  Failed to switch: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  const handlePluginsChanged = () => {
    // Reload active custom tabs & instruments lists
    loadWorkspace();
  };

  // Callback to import transcribed audio AI score
  const handleImportTranscribedScore = (notesText: string, useTwoMallets: boolean, syncData: any, audioPath: string) => {
    setProjectData((prev: any) => ({
      ...prev,
      notes: notesText,
      left_hand: useTwoMallets,
    }));
    callPython('import_transcribed_score_api', notesText, useTwoMallets, syncData, audioPath);
    setActiveTab('editor');
    setStatus('●  AI score imported successfully');
    setStatusLevel('ready');
  };

  return (
    <div className="flex h-screen w-screen bg-[var(--bg-app)] overflow-hidden text-[var(--text-main)]">
      {/* Sidebar navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={status}
        statusLevel={statusLevel}
        availableInstruments={availableInstruments}
        activeInstrument={activeInstrument}
        onInstrumentChange={handleInstrumentChange}
        pluginTabs={pluginTabs}
        onSave={handleSaveProject}
        onLoad={handleLoadProject}
      />

      {/* Main Panel views */}
      <div className="flex-1 h-full overflow-hidden flex flex-col">
        {activeTab === 'editor' && (
          <ScoreEditor
            projectData={projectData}
            setProjectData={setProjectData}
            activeNote={activeNote}
            setActiveNote={setActiveNote}
            activeLeftNote={activeLeftNote}
            setActiveLeftNote={setActiveLeftNote}
            isPlaying={isPlaying}
            setIsPlaying={setIsPlaying}
            status={status}
            setStatus={setStatus}
            setStatusLevel={setStatusLevel}
          />
        )}

        {activeTab === 'audio' && (
          <AudioAI
            setStatus={setStatus}
            setStatusLevel={setStatusLevel}
            onImportScore={handleImportTranscribedScore}
          />
        )}

        {activeTab === 'settings' && (
          <Settings
            setStatus={setStatus}
            setStatusLevel={setStatusLevel}
          />
        )}

        {activeTab === 'plugins' && (
          <Plugins
            setStatus={setStatus}
            setStatusLevel={setStatusLevel}
            onPluginsChanged={handlePluginsChanged}
          />
        )}

        {/* Dynamic Plugin Tab View Fallback */}
        {activeTab !== 'editor' && activeTab !== 'audio' && activeTab !== 'settings' && activeTab !== 'plugins' && (
          <div className="flex-1 h-full bg-[var(--bg-app)] p-8 flex flex-col items-center justify-center select-none space-y-4">
            <span className="text-5xl">🧩</span>
            <h2 className="text-[#d4af37] font-bold text-xl">
              {pluginTabs.find((t) => t.tab_id === activeTab)?.label || 'Plugin Tool'}
            </h2>
            <p className="text-gray-400 text-sm max-w-md text-center">
              This custom tab is registered dynamically by a Python plugin. 
              Actions triggered from here will execute background scripts directly in the Roneat API engine.
            </p>
            <button
              onClick={async () => {
                setStatus('●  Executing plugin action...');
                setStatusLevel('working');
                try {
                  const res = await callPython('trigger_custom_plugin_tab_action_api', activeTab);
                  setStatus(`●  Plugin Action complete: ${res || 'Success'}`);
                  setStatusLevel('ready');
                  loadWorkspace(); // Reload workspace in case data changed
                } catch (err: any) {
                  setStatus(`●  Execution failed: ${err.message || err}`);
                  setStatusLevel('error');
                }
              }}
              className="bg-[#d4af37] hover:bg-[#bfa032] text-black font-extrabold text-xs py-3 px-6 rounded-lg transition active:scale-98 cursor-pointer"
            >
              Run Plugin Tool
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
