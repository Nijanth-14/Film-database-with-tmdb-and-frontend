import React, { useState, useEffect, useRef } from 'react';
import './WavySlider.css';

export default function WavySlider({ media, position, duration, isPlaying, onChange, onHeartbeat }) {
  const [dominantColor, setDominantColor] = useState('#5ee0c0'); // Theme accent
  const imgRef = useRef(null);
  const containerRef = useRef(null);
  
  // Progress ratio (0 to 1)
  const progress = duration > 0 ? Math.min(position / duration, 1) : 0;
  
  // Extract color from media backdrop
  useEffect(() => {
    if (!media || !media.backdrop_path) return;
    
    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.src = `https://image.tmdb.org/t/p/w300${media.backdrop_path}`;
    
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, 64, 64);
        
        const data = ctx.getImageData(0, 0, 64, 64).data;
        let r = 0, g = 0, b = 0, count = 0;
        
        for (let i = 0; i < data.length; i += 16) {
          if (data[i+3] > 128) {
            r += data[i];
            g += data[i+1];
            b += data[i+2];
            count++;
          }
        }
        
        if (count > 0) {
          r = Math.floor(r / count);
          g = Math.floor(g / count);
          b = Math.floor(b / count);
          // Boost saturation and brightness a bit for the UI
          setDominantColor(`rgb(${Math.min(r + 30, 255)}, ${Math.min(g + 30, 255)}, ${Math.min(b + 50, 255)})`);
        }
      } catch (e) {
        console.error("Failed to extract color", e);
      }
    };
  }, [media]);

  const handlePointerDown = (e) => {
    containerRef.current.setPointerCapture(e.pointerId);
    updatePosition(e);
  };

  const handlePointerMove = (e) => {
    if (containerRef.current && containerRef.current.hasPointerCapture(e.pointerId)) {
      updatePosition(e);
    }
  };

  const handlePointerUp = (e) => {
    if (containerRef.current && containerRef.current.hasPointerCapture(e.pointerId)) {
      containerRef.current.releasePointerCapture(e.pointerId);
      if (onHeartbeat) onHeartbeat();
    }
  };

  const updatePosition = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const newProgress = x / rect.width;
    onChange(newProgress * duration);
  };

  return (
    <div 
      className="wavy-slider-container" 
      ref={containerRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      style={{ '--slider-color': dominantColor }}
    >
      <div className="wavy-slider-track" />
      
      {/* Wave element mask */}
      <div 
        className={`wavy-slider-wave-wrap ${isPlaying ? 'is-playing' : ''}`}
        style={{ width: `${progress * 100}%` }}
      >
        <div className="wavy-slider-wave" />
      </div>
      
      {/* Thumb indicator */}
      <div 
        className="wavy-slider-thumb"
        style={{ left: `${progress * 100}%`, backgroundColor: dominantColor }}
      />
    </div>
  );
}
