import React from 'react';

interface BeatItem {
  bar: number | null;
  left_bar: number | null;
  text: string;
  visual_text: string;
  visual_bar: string;
  barline: boolean;
  is_trem: boolean;
  repeat: number;
  is_line_rest: boolean;
  original_index: number;
}

interface ScoreGridProps {
  notesText: string;
  viewMode: 'Numeric' | 'Letters' | 'Syllabic';
  gridColumns: number;
  fontSize: number;
  leftHand: boolean;
  activeBeatIndex: number | null;
  onBeatClick?: (index: number) => void;
  title?: string;
  author?: string;
}

// Helper to translate note numbers to display text
const getNoteLabel = (note: number, mode: 'Numeric' | 'Letters' | 'Syllabic'): string => {
  const letters = ["KA", "KHA", "KO", "KHO", "NGO", "CA", "CHA", "CO", "CHO", "NYO", "DA", "DHA", "DO", "DHO", "NA", "TA", "THA", "TO", "THO", "NO", "BA"];
  const syllabic = ["Do", "Re", "Mi", "Fa", "Sol", "La", "Si", "Do", "Re", "Mi", "Fa", "Sol", "La", "Si", "Do", "Re", "Mi", "Fa", "Sol", "La", "Si"];

  const index = note - 1;
  if (index < 0 || index >= 21) return note.toString();

  switch (mode) {
    case 'Letters':
      return letters[index] || note.toString();
    case 'Syllabic':
      return syllabic[index] || note.toString();
    case 'Numeric':
    default:
      return note.toString();
  }
};

export const ScoreGrid: React.FC<ScoreGridProps> = ({
  notesText,
  viewMode,
  gridColumns,
  fontSize,
  leftHand,
  activeBeatIndex,
  onBeatClick,
  title = 'Untitled Score',
  author = 'Traditional',
}) => {
  // Parse the raw space-separated text into structured beats
  const parseNotes = (): BeatItem[] => {
    const rawTokens = notesText.replace(/\n/g, ' ').split(/\s+/).filter(Boolean);
    const beats: BeatItem[] = [];

    const TOK_RE = /^(\d+)(#(\d+))?$/;
    const LEFT_RIGHT_RE = /^\((\d+)\)(\d+)(#(\d+))?$/;

    rawTokens.forEach((tok, index) => {
      if (tok === '/') {
        if (beats.length > 0) {
          beats[beats.length - 1].barline = true;
        }
        return;
      }
      if (tok === '_') {
        beats.push({
          bar: null, left_bar: null,
          text: '_', visual_text: '_', visual_bar: '_',
          barline: false, is_trem: false, repeat: 1,
          is_line_rest: true, original_index: index,
        });
        return;
      }
      if (tok === '-' || tok === '0' || tok === 'x') {
        beats.push({
          bar: null, left_bar: null,
          text: '-', visual_text: '-', visual_bar: '-',
          barline: false, is_trem: false, repeat: 1,
          is_line_rest: false, original_index: index,
        });
        return;
      }

      // Check double mallet token, e.g. (8)1 or (8)1#3
      const m_lr = tok.match(LEFT_RIGHT_RE);
      if (m_lr) {
        const left_bar = parseInt(m_lr[1]);
        const bar = parseInt(m_lr[2]);
        const is_trem = !!m_lr[3];
        const repeat = m_lr[4] ? parseInt(m_lr[4]) : 1;
        const visual_bar = getNoteLabel(bar, viewMode);

        beats.push({
          bar, left_bar,
          text: tok,
          visual_text: is_trem ? `${visual_bar}~${repeat}` : visual_bar,
          visual_bar,
          barline: false, is_trem, repeat,
          is_line_rest: false, original_index: index,
        });
        return;
      }

      // Check standard token, e.g. 1 or 1#3
      const m = tok.match(TOK_RE);
      if (m) {
        const bar = parseInt(m[1]);
        const is_trem = !!m[2];
        const repeat = m[3] ? parseInt(m[3]) : 1;
        const visual_bar = getNoteLabel(bar, viewMode);

        beats.push({
          bar,
          left_bar: bar + 7 <= 21 ? bar + 7 : null,
          text: tok,
          visual_text: is_trem ? `${visual_bar}~${repeat}` : visual_bar,
          visual_bar,
          barline: false, is_trem, repeat,
          is_line_rest: false, original_index: index,
        });
      }
    });

    return beats;
  };

  const beats = parseNotes();

  // Group beats into rows based on column settings
  const rows: BeatItem[][] = [];
  for (let i = 0; i < beats.length; i += gridColumns) {
    rows.push(beats.slice(i, i + gridColumns));
  }

  // A4 Preview Sizing — Fixed width, A4 portrait ratio
  const page_w = 794; // A4 @ 96dpi = 793.7px
  const page_h = 1123; // A4 @ 96dpi portrait
  const margin = 56; // ~15mm margins
  const usable_w = page_w - margin * 2;

  const cell_w = usable_w / gridColumns;
  const cell_h = Math.min(58, Math.max(28, Math.floor(cell_w * 1.05)));
  const row_gap = 20;

  // Header heights
  const header_h_page1 = 110; // title block
  const header_h_other = 36; // small header for subsequent pages
  const footer_h = 32;

  // Rows per page (calculated separately for first/other pages)
  const usable_h_page1 = page_h - margin * 2 - header_h_page1 - footer_h;
  const usable_h_other = page_h - margin * 2 - header_h_other - footer_h;
  const rows_pp_first = Math.max(1, Math.floor(usable_h_page1 / (cell_h + row_gap)));
  const rows_pp_other = Math.max(1, Math.floor(usable_h_other / (cell_h + row_gap)));

  // Partition rows into pages
  const pages: BeatItem[][][] = [];
  let remaining = [...rows];

  const firstPageRows = remaining.splice(0, rows_pp_first);
  pages.push(firstPageRows);

  while (remaining.length > 0) {
    pages.push(remaining.splice(0, rows_pp_other));
  }

  // Ensure at least one empty page
  if (pages.length === 0) pages.push([]);

  const fontStyle = { fontSize: `${fontSize}px` };

  return (
    // Full-height container with its own vertical scroll
    <div
      className="w-full h-full overflow-y-auto flex flex-col items-center py-8 space-y-8 select-none"
      style={{ backgroundColor: 'var(--bg-app)' }}
    >
      {pages.map((pageRows, pageIndex) => (
        <div
          key={pageIndex}
          style={{
            width: `${page_w}px`,
            minHeight: `${page_h}px`,
            padding: `${margin}px`,
            boxSizing: 'border-box',
          }}
          className="bg-white text-black shadow-2xl rounded-sm relative flex flex-col"
        >
          {/* Header */}
          {pageIndex === 0 ? (
            // First page — large title block
            <div className="flex flex-col items-center mb-6 pb-4 border-b-2 border-gray-800">
              <h1
                style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: '26px', fontWeight: 'bold' }}
                className="text-gray-900 text-center uppercase tracking-widest mb-1"
              >
                {title || 'Untitled Score'}
              </h1>
              <div className="w-24 h-[1.5px] bg-gray-800 my-2" />
              {author && author.toLowerCase() !== 'anonymous' && (
                <p
                  style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontStyle: 'italic', fontSize: '13px' }}
                  className="text-gray-600"
                >
                  Composer: {author}
                </p>
              )}
            </div>
          ) : (
            // Subsequent pages — minimal header
            <div className="flex justify-between items-center mb-4 border-b border-gray-200 pb-2">
              <span
                style={{ fontFamily: 'Georgia, serif', fontStyle: 'italic', fontSize: '10px' }}
                className="text-gray-500 uppercase tracking-wider"
              >
                {title || 'Untitled Score'}
              </span>
              <span className="text-[9px] text-gray-400 font-mono">
                {viewMode} • {gridColumns} cols
              </span>
            </div>
          )}

          {/* Grid Rows */}
          <div className="flex-1 flex flex-col" style={{ gap: `${row_gap}px` }}>
            {pageRows.map((row, rowIndex) => (
              <div key={rowIndex} className="w-full">
                <div
                  className="flex"
                  style={{
                    borderTop: '1px solid #9ca3af',
                    borderLeft: '1px solid #9ca3af',
                    width: `${usable_w}px`,
                  }}
                >
                  {Array.from({ length: gridColumns }).map((_, colIndex) => {
                    const beat = row[colIndex];

                    if (!beat) {
                      return (
                        <div
                          key={`empty-${colIndex}`}
                          style={{
                            width: `${cell_w}px`,
                            height: `${cell_h}px`,
                            borderRight: '1px solid #9ca3af',
                            borderBottom: '1px solid #9ca3af',
                            flexShrink: 0,
                          }}
                          className="bg-gray-50/50"
                        />
                      );
                    }

                    const isActive = activeBeatIndex === beat.original_index;

                    return (
                      <div
                        key={beat.original_index}
                        onClick={() => onBeatClick && onBeatClick(beat.original_index)}
                        style={{
                          width: `${cell_w}px`,
                          height: `${cell_h}px`,
                          borderRight: beat.barline ? '2.5px solid #111' : '1px solid #9ca3af',
                          borderBottom: '1px solid #9ca3af',
                          flexShrink: 0,
                          position: 'relative',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          backgroundColor: isActive ? '#fef3c7' : undefined,
                          transition: 'background-color 0.1s',
                        }}
                        className="group hover:bg-amber-50/60"
                      >
                        {/* Left hand indicator */}
                        {leftHand && beat.left_bar !== null && beat.bar !== null && (
                          <span
                            style={{
                              position: 'absolute',
                              top: '2px',
                              left: 0,
                              right: 0,
                              textAlign: 'center',
                              fontSize: '7.5px',
                              color: '#1d4ed8',
                              fontWeight: 600,
                              fontFamily: 'system-ui, sans-serif',
                              letterSpacing: '-0.02em',
                              lineHeight: 1,
                            }}
                          >
                            ({getNoteLabel(beat.left_bar, viewMode)})
                          </span>
                        )}

                        {/* Main note value */}
                        <span
                          style={{
                            ...fontStyle,
                            fontFamily: 'Georgia, serif',
                            color: isActive ? '#92400e' : beat.is_trem ? '#78571a' : '#111111',
                            fontWeight: isActive || beat.is_trem ? '700' : '400',
                            transform: isActive ? 'scale(1.1)' : 'scale(1)',
                            transition: 'transform 0.1s',
                            lineHeight: 1,
                            marginTop: leftHand && beat.left_bar !== null ? '6px' : undefined,
                          }}
                        >
                          {beat.is_trem ? beat.visual_bar : beat.visual_text}
                        </span>

                        {/* Tremolo slash marks */}
                        {beat.is_trem && (
                          <div
                            style={{
                              position: 'absolute',
                              bottom: '3px',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '2px',
                            }}
                          >
                            <div style={{ width: '16px', height: '1.5px', backgroundColor: '#78571a', transform: 'rotate(-15deg)' }} />
                            <div style={{ width: '16px', height: '1.5px', backgroundColor: '#78571a', transform: 'rotate(-15deg)' }} />
                          </div>
                        )}

                        {/* Beat index tooltip on hover */}
                        <span
                          style={{
                            position: 'absolute',
                            bottom: 0,
                            fontSize: '6px',
                            color: '#9ca3af',
                            fontFamily: 'monospace',
                            opacity: 0,
                            transition: 'opacity 0.15s',
                          }}
                          className="group-hover:opacity-100"
                        >
                          #{beat.original_index + 1}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {/* Empty state for page 1 */}
            {beats.length === 0 && pageIndex === 0 && (
              <div
                className="flex flex-col items-center justify-center text-gray-400 border border-dashed border-gray-300 rounded-lg p-12 mt-4"
                style={{ minHeight: '200px' }}
              >
                <span className="text-4xl mb-3">🖊️</span>
                <p className="text-sm font-medium">No notes written yet.</p>
                <p className="text-xs mt-1">Type notes in the Score Text Editor on the left panel.</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="w-full flex justify-between items-center border-t border-gray-200 mt-4 pt-2"
            style={{ fontSize: '8px', color: '#9ca3af', fontFamily: 'Georgia, serif' }}
          >
            <span>Roneat Studio Pro — Xylophone Score Sheet</span>
            <span style={{ fontFamily: 'system-ui, sans-serif', fontWeight: 600, color: '#6b7280', fontSize: '9px' }}>
              — {pageIndex + 1} / {pages.length} —
            </span>
          </div>
        </div>
      ))}

      {/* Extra bottom padding */}
      <div style={{ height: '32px', flexShrink: 0 }} />
    </div>
  );
};
