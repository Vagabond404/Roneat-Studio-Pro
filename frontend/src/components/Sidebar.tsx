import React from 'react';
import { Music, Mic, Settings, Save, FolderOpen, Puzzle } from 'lucide-react';
import logoImg from '../assets/logo.png';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  status: string;
  statusLevel: 'ready' | 'working' | 'error';
  availableInstruments: [string, string][];
  activeInstrument: string;
  onInstrumentChange: (id: string) => void;
  pluginTabs: { tab_id: string; label: string; icon: string }[];
  onSave: () => void;
  onLoad: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  status,
  statusLevel,
  availableInstruments,
  activeInstrument,
  onInstrumentChange,
  pluginTabs,
  onSave,
  onLoad,
}) => {
  const getStatusColor = () => {
    switch (statusLevel) {
      case 'ready':
        return 'text-green-500';
      case 'working':
        return 'text-yellow-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-green-500';
    }
  };

  const navBtn = (tabId: string, icon: React.ReactNode, label: string) => (
    <button
      key={tabId}
      onClick={() => setActiveTab(tabId)}
      className={`w-full flex items-center px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 cursor-pointer ${
        activeTab === tabId
          ? 'bg-[var(--bg-hover)] text-[#d4af37] border-l-2 border-[#d4af37]'
          : 'text-[var(--text-main)] hover:bg-[var(--bg-hover-sidebar)] hover:text-[var(--text-title)]'
      }`}
    >
      <span className="w-4 h-4 mr-3 flex items-center justify-center">{icon}</span>
      <span>{label}</span>
    </button>
  );

  return (
    <div className="w-60 bg-[var(--bg-sidebar)] border-r border-[var(--border-sidebar)] h-full flex flex-col justify-between select-none">
      {/* Logo & Title */}
      <div className="flex flex-col items-center px-4 pt-5 pb-3">
        <div className="w-14 h-14 rounded-xl overflow-hidden border border-[var(--border-sidebar)] shadow-md mb-2 flex items-center justify-center bg-[var(--bg-key)]">
          <img
            src={logoImg}
            alt="Roneat Studio Pro"
            className="w-full h-full object-contain"
            onError={(e) => {
              // Fallback to emoji if image fails
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
        <h1 className="text-[#d4af37] font-extrabold text-xs tracking-widest uppercase text-center leading-tight">
          Roneat Studio
        </h1>
        <span className="text-[10px] text-[var(--text-dim)] font-bold tracking-[0.2em] mt-0.5">PRO</span>
        <div className="w-full h-[1px] bg-[var(--border-sidebar)] mt-4" />
      </div>

      {/* Main Navigation */}
      <div className="flex-1 px-3 py-1 overflow-y-auto space-y-0.5">
        {navBtn('editor', <Music className="w-4 h-4" />, 'Score Editor')}
        {navBtn('audio', <Mic className="w-4 h-4" />, 'Audio AI')}
        {navBtn('plugins', <Puzzle className="w-4 h-4" />, 'Plugins')}

        {/* Dynamic Plugin Tabs */}
        {pluginTabs.length > 0 && (
          <>
            <div className="text-[9px] uppercase font-extrabold text-[var(--text-dim)] tracking-widest px-4 pt-3 pb-1">
              Plugin Tools
            </div>
            {pluginTabs.map((tab) => (
              <button
                key={tab.tab_id}
                onClick={() => setActiveTab(tab.tab_id)}
                className={`w-full flex items-center px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 cursor-pointer ${
                  activeTab === tab.tab_id
                    ? 'bg-[var(--bg-hover)] text-[#d4af37] border-l-2 border-[#d4af37]'
                    : 'text-[var(--text-main)] hover:bg-[var(--bg-hover-sidebar)] hover:text-[var(--text-title)]'
                }`}
              >
                <span className="w-4 h-4 mr-3 text-center flex items-center justify-center text-base">
                  {tab.icon}
                </span>
                <span>{tab.label}</span>
              </button>
            ))}
          </>
        )}
      </div>

      {/* Bottom: Instrument, Settings, Save/Load, Status */}
      <div className="px-3 pb-4 border-t border-[var(--border-sidebar)] pt-3 space-y-2">
        {/* Instrument Selector */}
        {availableInstruments.length >= 2 && (
          <div className="space-y-1">
            <label className="text-[9px] font-extrabold text-[var(--text-dim)] uppercase tracking-widest block px-1">
              Instrument
            </label>
            <select
              value={activeInstrument}
              onChange={(e) => onInstrumentChange(e.target.value)}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-sidebar)] text-[var(--text-main)] text-xs font-semibold rounded-md px-3 py-1.5 outline-none focus:border-[#d4af37] transition duration-150 cursor-pointer"
            >
              {availableInstruments.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Settings Button */}
        <button
          onClick={() => setActiveTab('settings')}
          className={`w-full flex items-center px-4 py-2 rounded-lg text-xs font-bold transition-all duration-150 cursor-pointer ${
            activeTab === 'settings'
              ? 'bg-[var(--bg-hover)] text-[#d4af37]'
              : 'text-[var(--text-main)] hover:bg-[var(--bg-hover-sidebar)] hover:text-[var(--text-title)]'
          }`}
        >
          <Settings className="w-3.5 h-3.5 mr-2.5" />
          <span>Settings</span>
        </button>

        <div className="w-full h-[1px] bg-[var(--border-sidebar)]" />

        {/* Save & Load */}
        <button
          onClick={onSave}
          className="w-full bg-[#d4af37] hover:bg-[#c49f2d] text-black font-extrabold text-xs py-2 px-4 rounded flex items-center justify-center space-x-2 transition duration-150 shadow active:scale-95 cursor-pointer"
        >
          <Save className="w-3.5 h-3.5" />
          <span>Save Project</span>
        </button>
        <button
          onClick={onLoad}
          className="w-full bg-transparent hover:bg-[var(--bg-hover-sidebar)] text-[var(--text-main)] border border-[var(--border-sidebar)] font-semibold text-xs py-2 px-4 rounded flex items-center justify-center space-x-2 transition duration-150 active:scale-95 cursor-pointer"
        >
          <FolderOpen className="w-3.5 h-3.5" />
          <span>Load Project</span>
        </button>

        {/* Status Indicator */}
        <div className={`flex items-center space-x-1.5 px-1 text-[10px] font-mono ${getStatusColor()}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current inline-block animate-pulse" />
          <span className="truncate">{status}</span>
        </div>
      </div>
    </div>
  );
};
