import React, { useEffect, useRef, useState } from 'react';
import { Home, Flame, Film, Plus, Play, Pause, LogOut } from 'lucide-react';
import './FloatingDock.css';

export default function FloatingDock({ user, onLogout, onSwitchProfile, onAddMedia, activeMedia,
  isPlaying, setIsPlaying, position, formatTime }) {
  const [visible, setVisible] = useState(true);
  const nav = useRef(null);
  useEffect(() => {
    let previous = window.scrollY;
    const onScroll = () => {
      const current = window.scrollY;
      if (Math.abs(current - previous) < 8) return;
      if (!nav.current?.matches(':hover') && !nav.current?.contains(document.activeElement)) {
        setVisible(current < previous || current < 60);
      }
      previous = current;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  const scrollTo = id => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  const items = [
    { label: 'Home', icon: Home, click: () => window.scrollTo({ top: 0, behavior: 'smooth' }) },
    { label: 'Trending', icon: Flame, click: () => scrollTo('trending') },
    { label: 'Catalog', icon: Film, click: () => scrollTo('catalog') },
    ...(user.is_admin ? [{ label: 'Add Media', icon: Plus, click: onAddMedia }] : []),
  ];
  return <nav ref={nav} onFocusCapture={() => setVisible(true)} className={`dock-container ${visible ? 'is-visible' : 'is-hidden'}`} aria-label="Library navigation">
    <div className="dock-content">
      <span className="dock-brand">STREAM</span>
      <div className="dock-divider" />
      {items.map(({ label, icon: Icon, click }) => <button key={label} aria-label={label}
        className="dock-icon-wrapper" type="button" onClick={click}>
        <div className="dock-icon"><Icon size={20} strokeWidth={2} /></div>
        <span className="dock-tooltip">{label}</span>
      </button>)}
      {activeMedia && <>
        <div className="dock-divider" />
        <div className="dock-mini-player">
          <button className="dock-mini-play-btn" aria-label={isPlaying ? 'Pause' : 'Play'}
            onClick={() => setIsPlaying(!isPlaying)}>{isPlaying ? <Pause size={14} /> : <Play size={14} />}</button>
          <div className="dock-mini-info"><span className="dock-mini-title">{activeMedia.title}</span>
            <span className="dock-mini-time">{formatTime(position)}</span></div>
        </div>
      </>}
      <div className="dock-divider" />
      <button type="button" className="dock-icon-wrapper dock-user-btn" onClick={onSwitchProfile}
        aria-label={'Switch profile. Current profile: ' + user.username}>
        <span className="dock-user-avatar">{user.username[0].toUpperCase()}</span>
        <span className="dock-tooltip">Switch profile · {user.username}</span>
      </button>
      <button aria-label="Sign out" className="dock-icon-wrapper" onClick={onLogout}>
        <div className="dock-icon"><LogOut size={18} /></div><span className="dock-tooltip">Sign out</span>
      </button>
    </div>
  </nav>;
}
