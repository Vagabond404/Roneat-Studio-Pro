// TypeScript declarations for Eel
declare global {
  interface Window {
    eel: {
      _start_geometry?: () => void;
      expose: (fn: Function, name?: string) => void;
      [key: string]: any;
    };
  }
}

// Helper to check if Eel is running (avoids crashing in standalone browser testing)
export const isEelAvailable = (): boolean => {
  return typeof window !== 'undefined' && typeof window.eel !== 'undefined';
};

/**
 * Safe wrapper to invoke a python function exposed via Eel.
 * @param functionName Name of the exposed Python function.
 * @param args Arguments to pass.
 * @returns A promise resolving to the return value of the Python function, or mock fallback.
 */
export async function callPython<T = any>(functionName: string, ...args: any[]): Promise<T> {
  if (!isEelAvailable()) {
    console.warn(`[Eel Mock] Calling ${functionName} with args:`, args);
    return getMockFallback(functionName, args);
  }

  const pyFunc = window.eel[functionName];
  if (!pyFunc) {
    console.error(`[Eel Error] Python function "${functionName}" is not exposed.`);
    throw new Error(`Python function "${functionName}" not found.`);
  }

  return new Promise<T>((resolve, reject) => {
    try {
      pyFunc(...args)((response: T) => {
        resolve(response);
      });
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Register a JavaScript function so it can be called from Python using `eel.js_func(...)`.
 * @param name Name of the function to expose.
 * @param fn The function implementation.
 */
export function exposeToPython(name: string, fn: Function): void {
  if (!isEelAvailable()) {
    console.warn(`[Eel Mock] Exposing function "${name}" to Python.`);
    return;
  }
  window.eel.expose(fn, name);
  console.log(`[Eel] Function "${name}" exposed to Python successfully.`);
}

// Fallback mocks for when running React UI standalone (without Python backend)
function getMockFallback(functionName: string, _args: any[]): any {
  switch (functionName) {
    case 'get_settings':
      return { theme: 'Dark', language: 'fr', hz_tuning: 440 };
    case 'get_project_data':
      return {
        title: "Happy Birthday",
        author: "Traditionnel",
        notes: "1 1 2 1 4 3 / 1 1 2 1 5 4 / 1 1 8 6 4 3 2 / 10 10 9 6 7 6",
        bpm: "170",
        grid: "8 columns",
        measure: "4/4",
        font_size: 16,
        accent: "#D4AF37",
        left_hand: false,
        show_nums: true,
        hits_sec: "16",
        instrument_id: "roneat_ek"
      };
    case 'get_available_instruments':
      return [
        ['roneat_ek', 'Roneat Ek (Standard)'],
        ['roneat_thung', 'Roneat Thung (Bass)']
      ];
    case 'get_installed_plugins':
      return [
        { id: 'roneat_ek_standard', name: 'Roneat Ek Engine', version: '1.0.0', author: 'Khmer Audio', description: 'Cambodian Roneat Ek traditional sound and layout.', active: true },
        { id: 'transpose_plugin', name: 'Score Transposer', version: '1.1.0', author: 'Roneat Pro Team', description: 'Transposes musical notes up or down.', active: true }
      ];
    case 'is_playing':
      return false;
    default:
      return null;
  }
}
