/**
 * CVDChart — Cumulative Volume Delta chart (canvas-based, pannello inferiore).
 */
import React, { useRef, useEffect, useMemo } from 'react';
import { useTradingStore } from '../store/tradingStore';

interface CVDChartProps {
  height?: number;
}

export const CVDChart: React.FC<CVDChartProps> = ({ height = 100 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { candles } = useTradingStore();

  const cvdValues = useMemo(() => candles.map(c => c.barCvd), [candles]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;

    // Imposta dimensione canvas per DPR
    canvas.width  = W * (window.devicePixelRatio || 1);
    canvas.height = H * (window.devicePixelRatio || 1);
    ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#070c18';
    ctx.fillRect(0, 0, W, H);

    if (cvdValues.length < 2) {
      ctx.fillStyle = '#334155';
      ctx.font = '10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('CVD — In attesa dati...', W / 2, H / 2);
      return;
    }

    const minCVD = Math.min(...cvdValues, 0);
    const maxCVD = Math.max(...cvdValues, 0);
    const range  = maxCVD - minCVD || 1;

    const toX = (i: number) => (i / (cvdValues.length - 1)) * (W - 8) + 4;
    const toY = (v: number) => H * 0.9 - ((v - minCVD) / range) * H * 0.8;
    const zeroY = toY(0);

    // Zero line
    ctx.strokeStyle = '#334155';
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(W, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Area fill verde
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, 'rgba(52, 211, 153, 0.35)');
    grad.addColorStop(1, 'rgba(52, 211, 153, 0.02)');

    ctx.beginPath();
    ctx.moveTo(toX(0), zeroY);
    cvdValues.forEach((v, i) => {
      if (i === 0) ctx.lineTo(toX(i), toY(v));
      else         ctx.lineTo(toX(i), toY(v));
    });
    ctx.lineTo(toX(cvdValues.length - 1), zeroY);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth   = 1.5;
    ctx.lineJoin    = 'round';
    ctx.beginPath();
    cvdValues.forEach((v, i) => {
      if (i === 0) ctx.moveTo(toX(i), toY(v));
      else         ctx.lineTo(toX(i), toY(v));
    });
    ctx.stroke();

    // Labels
    const lastCVD = cvdValues[cvdValues.length - 1];
    ctx.fillStyle  = '#94a3b8';
    ctx.font       = '9px monospace';
    ctx.textAlign  = 'left';
    ctx.fillText(`CVD: ${lastCVD >= 0 ? '+' : ''}${lastCVD}`, 6, 13);
    ctx.textAlign  = 'right';
    ctx.fillStyle  = '#475569';
    ctx.fillText(`max:+${maxCVD}`, W - 4, 13);
    ctx.fillText(`min:${minCVD}`, W - 4, H - 4);

  }, [cvdValues]);

  return (
    <div style={{ height }} className="bg-[#070c18] border-t border-slate-800/80 shrink-0 relative w-full overflow-hidden">
      <div className="absolute top-1 left-10 text-[9px] text-slate-600 font-bold tracking-widest z-10 pointer-events-none">
        CVD
      </div>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />
    </div>
  );
};
