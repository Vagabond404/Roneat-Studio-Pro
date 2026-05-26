import React, { useState, useEffect } from 'react';
import { Puzzle, Check, X, RefreshCw, Upload } from 'lucide-react';
import { callPython } from '../eel';

interface PluginItem {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  active: boolean;
}

interface PluginsProps {
  setStatus: (s: string) => void;
  setStatusLevel: (level: 'ready' | 'working' | 'error') => void;
  onPluginsChanged: () => void;
}

export const Plugins: React.FC<PluginsProps> = ({
  setStatus,
  setStatusLevel,
  onPluginsChanged,
}) => {
  const [plugins, setPlugins] = useState<PluginItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadPluginsList = async () => {
    setIsLoading(true);
    try {
      const list = await callPython<PluginItem[]>('get_installed_plugins_api');
      if (list) {
        setPlugins(list);
      }
    } catch (err) {
      console.error('Failed to load plugins:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPluginsList();
  }, []);

  const handleToggleActive = async (id: string, currentActive: boolean) => {
    setStatus(`●  Updating plugin ${id}...`);
    setStatusLevel('working');
    try {
      const success = await callPython('toggle_plugin_active_api', id, !currentActive);
      if (success) {
        setStatus(`●  Plugin ${id} ${!currentActive ? 'enabled' : 'disabled'}`);
        setStatusLevel('ready');
        await loadPluginsList();
        // Notify parent to update registered tabs/dropdowns
        onPluginsChanged();
      }
    } catch (err: any) {
      setStatus(`●  Error: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  const handleInstallPlugin = async () => {
    try {
      const filePath = await callPython('select_zip_file_dialog');
      if (filePath) {
        setStatus('●  Installing plugin...');
        setStatusLevel('working');
        const success = await callPython('install_plugin_zip_api', filePath);
        if (success) {
          setStatus('●  Plugin installed successfully');
          setStatusLevel('ready');
          await loadPluginsList();
          onPluginsChanged();
        } else {
          setStatus('●  Failed to install plugin');
          setStatusLevel('error');
        }
      }
    } catch (err: any) {
      setStatus(`●  Installation failed: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  const handleReloadAll = async () => {
    setStatus('●  Reloading all plugins...');
    setStatusLevel('working');
    try {
      await callPython('reload_all_plugins_api');
      setStatus('●  Plugins reloaded successfully');
      setStatusLevel('ready');
      await loadPluginsList();
      onPluginsChanged();
    } catch (err: any) {
      setStatus(`●  Reload failed: ${err.message || err}`);
      setStatusLevel('error');
    }
  };

  return (
    <div className="flex-1 h-full overflow-y-auto bg-[#121212] p-8 select-none">
      
      {/* HEADER */}
      <div className="max-w-4xl mx-auto mb-8 flex justify-between items-end">
        <div>
          <div className="flex items-center space-x-3 mb-2">
            <span className="text-3xl">🧩</span>
            <h1 className="text-white text-3xl font-extrabold tracking-tight">Plugin Ecosystem</h1>
          </div>
          <p className="text-gray-400 text-sm">
            Extend Roneat Studio Pro features with community plugins for transcription, custom instruments, and score analysis.
          </p>
        </div>

        <div className="flex space-x-2">
          {/* Reload Button */}
          <button
            onClick={handleReloadAll}
            className="bg-transparent hover:bg-[#252526] text-[#d4af37] border border-[#d4af37]/30 hover:border-[#d4af37] font-bold text-xs py-2 px-4 rounded flex items-center space-x-1.5 transition active:scale-98 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload All</span>
          </button>
          
          {/* Install Button */}
          <button
            onClick={handleInstallPlugin}
            className="bg-[#d4af37] hover:bg-[#bfa032] text-black font-extrabold text-xs py-2 px-4 rounded flex items-center space-x-1.5 transition shadow-md active:scale-98 cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Install Plugin (.zip)</span>
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        <div className="h-[1px] bg-[#2e303a] w-full mb-6" />

        {/* LOADING STATE */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 space-y-4">
            <div className="w-10 h-10 border-4 border-gray-800 border-t-[#d4af37] rounded-full animate-spin" />
            <span className="text-xs text-gray-500 font-mono">Scanning plugins folder...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {plugins.map((plugin) => (
              <div 
                key={plugin.id}
                className={`bg-[#1e1e1e] border rounded-2xl p-5 flex flex-col justify-between transition duration-200 ${
                  plugin.active ? 'border-[#d4af37]/30 shadow-md' : 'border-[#2e303a] opacity-70'
                }`}
              >
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <div className="space-y-0.5">
                      <h3 className="text-white text-sm font-bold flex items-center space-x-1.5">
                        <span>{plugin.name}</span>
                        {plugin.id === 'roneat_ek_standard' && (
                          <span className="bg-[#d4af37]/15 text-[#d4af37] text-[8px] font-extrabold px-1.5 py-0.5 rounded tracking-wide uppercase">
                            Core
                          </span>
                        )}
                      </h3>
                      <p className="text-[10px] text-gray-500 font-mono">
                        v{plugin.version} • By {plugin.author}
                      </p>
                    </div>

                    {/* Toggle Switch */}
                    <label className="relative inline-flex items-center cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={plugin.active}
                        disabled={plugin.id === 'roneat_ek_standard'} // Don't let user disable the core instrument plugin
                        onChange={() => handleToggleActive(plugin.id, plugin.active)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-[#16171d] rounded-full peer peer-focus:ring-0 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-gray-400 after:border-gray-300 after:border after:rounded-full after:height-4 after:width-4 after:transition-all peer-checked:bg-[#d4af37] peer-checked:after:bg-black peer-checked:after:border-black cursor-pointer" />
                    </label>
                  </div>

                  <p className="text-xs text-gray-400 leading-relaxed mt-2.5">
                    {plugin.description}
                  </p>
                </div>

                <div className="flex items-center justify-between border-t border-[#2e303a] mt-4 pt-3.5 text-[10px] text-gray-500 font-mono">
                  <span>ID: {plugin.id}</span>
                  <span className={`flex items-center ${plugin.active ? 'text-green-500' : 'text-gray-500'}`}>
                    {plugin.active ? (
                      <>
                        <Check className="w-3 h-3 mr-1" />
                        <span>Active</span>
                      </>
                    ) : (
                      <>
                        <X className="w-3 h-3 mr-1" />
                        <span>Disabled</span>
                      </>
                    )}
                  </span>
                </div>
              </div>
            ))}

            {plugins.length === 0 && (
              <div className="md:col-span-2 border-2 border-dashed border-[#2e303a] rounded-2xl p-12 text-center text-gray-500 flex flex-col items-center justify-center space-y-3">
                <Puzzle className="w-12 h-12 text-gray-600" />
                <h3 className="text-sm font-bold text-white">No plugins loaded</h3>
                <p className="text-xs max-w-sm">
                  Click the 'Install Plugin' button to upload a package ZIP file.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
};
