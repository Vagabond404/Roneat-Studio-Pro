import React, { useState, useEffect, useRef } from 'react';

interface RoneatKeyboardProps {
  mode: 'playback' | 'edit' | 'jam';
  twoMallets: boolean;
  minNote?: number;
  maxNote?: number;
  activeNote: number | null;
  activeLeftNote: number | null;
  accentColor: string;
  onNoteTriggered?: (note: number, repeat?: number) => void;
  showNumbers: boolean;
  viewMode: 'Numeric' | 'Letters' | 'Syllabic';
}

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

export const RoneatKeyboard: React.FC<RoneatKeyboardProps> = ({
  mode,
  twoMallets,
  minNote = 1,
  maxNote = 21,
  activeNote,
  activeLeftNote,
  accentColor = '#d4af37',
  onNoteTriggered,
  showNumbers,
  viewMode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 350 });
  const [hoveredNote, setHoveredNote] = useState<number | null>(null);
  const [pressedNote, setPressedNote] = useState<number | null>(null);
  const [pressTime, setPressTime] = useState<number | null>(null);
  const [tremoloRepeat, setTremoloRepeat] = useState<number>(0);
  const tremoloTimer = useRef<number | null>(null);

  // Resize listener
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight || 350,
        });
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const nBars = maxNote - minNote + 1;
  const isCircularInstrument = maxNote === 16; // Detect Kong Thom (16 keys)

  // Hand highlight helpers
  const isRightHandActive = (note: number) => {
    if (pressedNote === note) return true;
    if (mode === 'playback' && activeNote === note) return true;
    return false;
  };

  const isLeftHandActive = (note: number) => {
    if (twoMallets && pressedNote !== null && note === pressedNote + 7) return true;
    if (mode === 'playback' && twoMallets && activeLeftNote === note) return true;
    if (mode === 'playback' && twoMallets && activeNote !== null && note === activeNote + 7) return true;
    return false;
  };

  // Tremolo hold tracker
  const checkTremolo = (currentPressTime: number) => {
    const held = (Date.now() - currentPressTime) / 1000;
    const threshold = 0.4;
    if (held >= threshold) {
      const extra = held - threshold;
      const repeats = Math.max(2, Math.min(32, 2 + Math.floor(extra / 0.18)));
      setTremoloRepeat(repeats);
    }
    tremoloTimer.current = window.setTimeout(() => checkTremolo(currentPressTime), 80);
  };

  const handleMouseDown = (note: number) => {
    setPressedNote(note);
    const now = Date.now();
    setPressTime(now);
    setTremoloRepeat(0);

    if (onNoteTriggered) {
      onNoteTriggered(note);
    }

    if (mode === 'edit') {
      if (tremoloTimer.current) clearTimeout(tremoloTimer.current);
      checkTremolo(now);
    }
  };

  const handleMouseUp = () => {
    if (tremoloTimer.current) {
      clearTimeout(tremoloTimer.current);
      tremoloTimer.current = null;
    }

    const note = pressedNote;
    const start = pressTime;

    setPressedNote(null);
    setPressTime(null);
    setTremoloRepeat(0);

    if (note === null || start === null) return;

    if (mode === 'edit' && onNoteTriggered) {
      const held = (Date.now() - start) / 1000;
      const threshold = 0.4;
      if (held >= threshold) {
        const repeats = Math.max(2, Math.min(32, 2 + Math.floor((held - threshold) / 0.18)));
        onNoteTriggered(note, repeats);
      } else {
        onNoteTriggered(note, 1);
      }
    }
  };

  const handleMouseLeaveKeyboard = () => {
    setHoveredNote(null);
    if (pressedNote !== null) {
      handleMouseUp();
    }
  };

  // ── DRAW CIRCULAR INSTRUMENT (KONG THOM - 16 gongs) ───────────────────────
  const renderCircularKeyboard = () => {
    const center_x = dimensions.width / 2;
    const center_y = dimensions.height * 0.65;
    const usable_width = dimensions.width * 0.85;
    const usable_height = dimensions.height * 0.65;
    const radius = Math.min(usable_width / 2, usable_height) * 0.95;

    const start_angle_deg = 20;
    const end_angle_deg = 160;
    const total_arc_deg = end_angle_deg - start_angle_deg;
    const angle_per_gong = total_arc_deg / (nBars - 1 || 1);
    const gong_radius = Math.max(12, radius / 16);

    // Calculate arc path coordinates for the mounting rails
    const rail_radius_outer = radius + 10;
    const rail_radius_inner = radius - 10;
    const outer_pts: string[] = [];
    const inner_pts: string[] = [];

    for (let i = 0; i < nBars; i++) {
      const angle_deg = start_angle_deg + i * angle_per_gong;
      const angle_rad = (angle_deg * Math.PI) / 180;
      
      const ox = center_x + rail_radius_outer * Math.cos(angle_rad);
      const oy = center_y - rail_radius_outer * Math.sin(angle_rad);
      outer_pts.push(`${ox},${oy}`);

      const ix = center_x + rail_radius_inner * Math.cos(angle_rad);
      const iy = center_y - rail_radius_inner * Math.sin(angle_rad);
      inner_pts.unshift(`${ix},${iy}`); // Reverse order for closed polygon
    }

    const railPointsStr = [...outer_pts, ...inner_pts].join(' ');

    const gongs = Array.from({ length: nBars }).map((_, i) => {
      const gongNum = minNote + i; // 1 to 16
      const angle_deg = start_angle_deg + i * angle_per_gong;
      const angle_rad = (angle_deg * Math.PI) / 180;
      
      const gx = center_x + radius * Math.cos(angle_rad);
      const gy = center_y - radius * Math.sin(angle_rad);
      const cord_top_y = gy - gong_radius - 8;

      return { gongNum, gx, gy, cord_top_y };
    });

    return (
      <svg width={dimensions.width} height={dimensions.height} className="select-none">
        {/* Draw Circular Rail Arc */}
        {gongs.length > 0 && (
          <polygon
            points={railPointsStr}
            fill="#5A4A3A"
            stroke="#3e2d1d"
            strokeWidth={1}
          />
        )}

        {/* Draw Gongs */}
        {gongs.map(({ gongNum, gx, gy, cord_top_y }) => {
          const isRH = isRightHandActive(gongNum);
          const isLH = isLeftHandActive(gongNum);
          const isHovered = hoveredNote === gongNum && !isRH;
          const isHoveredLH = hoveredNote !== null && twoMallets && gongNum === hoveredNote + 7 && !isLH;

          let faceColor = '#D2B48C'; // Bronze gold face
          let edgeColor = '#8B4513'; // Darker bronze shadow

          if (isRH) {
            faceColor = accentColor;
            edgeColor = '#8e7611';
          } else if (isLH) {
            faceColor = '#3b82f6';
            edgeColor = '#1d4ed8';
          } else if (isHovered) {
            faceColor = '#d4af37';
            edgeColor = '#8e7611';
          } else if (isHoveredLH) {
            faceColor = '#60a5fa';
            edgeColor = '#3b82f6';
          }

          return (
            <g
              key={gongNum}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredNote(gongNum)}
              onMouseDown={() => handleMouseDown(gongNum)}
            >
              {/* Suspension Cord */}
              <line
                x1={gx}
                y1={cord_top_y}
                x2={gx}
                y2={gy - gong_radius}
                stroke="#666666"
                strokeWidth={1}
              />

              {/* Gong Base Shadow */}
              <circle
                cx={gx}
                cy={gy}
                r={gong_radius}
                fill={edgeColor}
              />

              {/* Gong Face (gradient representation) */}
              <circle
                cx={gx}
                cy={gy}
                r={gong_radius * 0.9}
                fill={faceColor}
              />

              {/* Gong Boss (the center nipple/bump on a bossed gong) */}
              <circle
                cx={gx}
                cy={gy}
                r={gong_radius * 0.35}
                fill={isRH || isLH ? '#ffffff' : '#f5f5f5'}
                opacity={0.8}
              />

              {/* Gong Label text */}
              {showNumbers && (
                <text
                  x={gx}
                  y={gy + gong_radius + 16}
                  fill={isRH || isLH ? accentColor : '#c8a96e'}
                  fontSize={Math.max(9, gong_radius * 0.9)}
                  fontWeight="bold"
                  textAnchor="middle"
                  fontFamily="monospace"
                >
                  {getNoteLabel(gongNum, viewMode)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  // ── DRAW FLAT KEYBOARD (RONEAT EK - 21 bars) ──────────────────────────────
  const renderFlatKeyboard = () => {
    const marginX = 20;
    const marginY = 40;
    const totalW = dimensions.width - marginX * 2;
    const gap = 4;
    const barW = nBars > 0 ? (totalW - gap * (nBars - 1)) / nBars : totalW;
    const availH = dimensions.height - marginY * 2 - 20;

    const minBarH = availH * 0.35;
    const maxBarH = availH * 0.85;
    const railY = marginY;
    const railH = 10;

    const bars = Array.from({ length: nBars }).map((_, i) => {
      const barNum = maxNote - i;
      const t = i / (nBars - 1 || 1);
      const bh = maxBarH - t * (maxBarH - minBarH);
      const xl = marginX + i * (barW + gap);
      const xr = xl + barW;
      const yt = railY + railH;
      const yb = yt + bh;
      const cx = (xl + xr) / 2;

      return { barNum, xl, xr, yt, yb, cx, bh };
    });

    return (
      <svg width={dimensions.width} height={dimensions.height} className="select-none">
        {/* Draw Support Rail */}
        {bars.length > 0 && (
          <rect
            x={bars[0].xl - 8}
            y={railY}
            width={bars[bars.length - 1].xr - bars[0].xl + 16}
            height={railH}
            rx={4}
            fill="#3e3e42"
          />
        )}

        {/* Draw Bars */}
        {bars.map(({ barNum, xl, yt, yb, cx, bh }) => {
          const isRH = isRightHandActive(barNum);
          const isLH = isLeftHandActive(barNum);
          const isHovered = hoveredNote === barNum && !isRH;
          const isHoveredLH = hoveredNote !== null && twoMallets && barNum === hoveredNote + 7 && !isLH;

          let fill = '#2a2d2e';
          let stroke = '#1e1e1f';

          if (isRH) {
            fill = accentColor;
            stroke = '#8e7611';
          } else if (isLH) {
            fill = '#3db87a'; // Green/Success for left hand in standard mode
            stroke = '#23734c';
          } else if (isHovered) {
            fill = '#d4af37';
            stroke = '#8e7611';
          } else if (isHoveredLH) {
            fill = '#5cd69a';
            stroke = '#3db87a';
          }

          const tubeRadius = Math.max(3, Math.min(barW * 0.35, 10));
          const tubeCY = yb + tubeRadius + 8 + ((maxNote - barNum) % 2 === 0 ? 0 : 4);

          return (
            <g
              key={barNum}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredNote(barNum)}
              onMouseDown={() => handleMouseDown(barNum)}
            >
              {/* Bar Shadow */}
              <rect
                x={xl}
                y={yt}
                width={barW}
                height={bh}
                rx={3}
                fill={stroke}
              />

              {/* Bar Face */}
              <rect
                x={xl + 1.5}
                y={yt + 1}
                width={barW - 3}
                height={bh - 4}
                rx={2.5}
                fill={fill}
              />

              {/* String line */}
              <line
                x1={cx}
                y1={yb}
                x2={cx}
                y2={tubeCY - tubeRadius}
                stroke="#4a4a4a"
                strokeWidth={1.5}
              />

              {/* hanging ball */}
              <circle
                cx={cx}
                cy={tubeCY}
                r={tubeRadius}
                fill={isRH || isLH ? fill : '#3a3a3c'}
                stroke={isRH || isLH ? stroke : '#2a2d2e'}
                strokeWidth={1}
              />

              {/* text */}
              {showNumbers && (
                <text
                  x={cx}
                  y={tubeCY + tubeRadius + 14}
                  fill={isRH || isLH ? accentColor : '#888888'}
                  fontSize={Math.max(9, Math.min(barW * 0.45, 13))}
                  fontWeight="bold"
                  textAnchor="middle"
                  fontFamily="monospace"
                >
                  {getNoteLabel(barNum, viewMode)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[350px] bg-[#16171d] rounded-lg border border-[#2e303a] p-4 flex flex-col items-center justify-center relative overflow-hidden"
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeaveKeyboard}
    >
      {/* HUD overlay for Edit mode tremolo indicator */}
      {mode === 'edit' && tremoloRepeat > 0 && (
        <div className="absolute top-4 right-4 bg-[#d4af37]/15 border border-[#d4af37]/40 px-3 py-1.5 rounded text-xs font-bold text-[#d4af37] animate-pulse">
          Tremolo: {tremoloRepeat} hits
        </div>
      )}

      {isCircularInstrument ? renderCircularKeyboard() : renderFlatKeyboard()}
    </div>
  );
};
