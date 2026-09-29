import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Play, X, Flame, TrendingUp, Film, Sparkles, Star, Users } from 'lucide-react';
import FloatingDock from './components/FloatingDock';
import ProfileSwitcher from './components/ProfileSwitcher';
import PlayerModal from './components/PlayerModal';
import SeriesModal from './components/SeriesModal';
import AddMediaModal from './components/AddMediaModal';
import { api } from './api';



const formatTime = (seconds) => {
  if (!seconds) return '0:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

const getGenreStyle = () => ({ bg: 'bg-white/5', text: 'text-white/70', border: 'border-white/10' });

export default function App({ user, onLogout, onProfileChange }) {
  const currentUser = String(user.id);
  const [showProfiles, setShowProfiles] = useState(false);
  const [dashboard, setDashboard] = useState([]);
  const [trending, setTrending] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [genres, setGenres] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('');
  const [activeMedia, setActiveMedia] = useState(null);
  const [activeSeries, setActiveSeries] = useState(null);
  const openEntry = item => {
    if (item.media_type === 'tv') setActiveSeries(item);
    else setActiveMedia(item);
  };
  const [showAddModal, setShowAddModal] = useState(false);
  const [playerIsPlaying, setPlayerIsPlaying] = useState(false);
  const [playerPosition, setPlayerPosition] = useState(0);
  const [nextCursor, setNextCursor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef(0);
  const filteredCatalog = catalog;

  const fetchDashboard = async () => {
    try { setDashboard(await api('/dashboard')); } catch (e) { setError(e.message); }
  };
  const fetchTrending = async () => {
    try { setTrending(await api('/trending')); } catch (e) { setError(e.message); }
  };
  const fetchCatalog = async (after = 0) => {
    const id = ++requestId.current;
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ q: searchQuery, genre: selectedGenre, after, limit: 24 });
      const data = await api('/catalog?' + params);
      if (id !== requestId.current) return;
      setCatalog(previous => after ? [...previous, ...data.items] : data.items);
      setNextCursor(data.next_cursor);
      setGenres(await api('/genres'));
    } catch (e) { if (id === requestId.current) setError(e.message); }
    finally { if (id === requestId.current) setLoading(false); }
  };
  useEffect(() => { fetchDashboard(); fetchTrending(); }, []);
  useEffect(() => {
    const timer = setInterval(async () => {
      const visible = [...catalog, ...trending, ...dashboard];
      const ids = [...new Set(visible.filter(item =>
        ['pending', 'preparing'].includes(item.playback_status) ||
        ['pending', 'processing'].includes(item.metadata_status)).map(item => item.id))];
      if (!ids.length) return;
      const updates = await Promise.all(ids.map(id => api('/catalog/' + id).catch(() => null)));
      const patch = items => items.map(item => {
        const update = updates.find(value => value?.id === item.id);
        return update ? { ...item, ...update } : item;
      });
      setCatalog(patch); setTrending(patch); setDashboard(patch);
    }, 2500);
    return () => clearInterval(timer);
  }, [catalog, trending, dashboard]);

  useEffect(() => {
    ++requestId.current;
    setNextCursor(null);
    const timer = setTimeout(() => fetchCatalog(), 250);
    return () => { clearTimeout(timer); ++requestId.current; };
  }, [searchQuery, selectedGenre]);

  return (
    <div className="min-h-screen pb-12 flex flex-col relative overflow-hidden">
      <div className="forest-bg"></div>

      {/* Floating Dock */}
      <FloatingDock
        currentUser={currentUser}
        user={user}
        onLogout={onLogout}
        onSwitchProfile={() => setShowProfiles(true)}
        onAddMedia={() => setShowAddModal(true)}
        activeMedia={activeMedia}
        isPlaying={playerIsPlaying}
        setIsPlaying={setPlayerIsPlaying}
        position={playerPosition}
        setPosition={setPlayerPosition}
        formatTime={formatTime}
      />

      {showProfiles && <ProfileSwitcher user={user} onClose={() => setShowProfiles(false)} onSelect={onProfileChange} />}
      <main className="flex-grow pt-16 pb-32 px-6 lg:px-12 space-y-16 relative z-10">
        <header className="relative pr-0 sm:pr-44">
          <button type="button" onClick={() => setShowProfiles(true)} className="mb-5 sm:mb-0 sm:absolute sm:right-0 sm:top-0 inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm text-white/90 hover:bg-white/10"><Users size={17} />Switch profile</button>
          <p className="text-accent-soft text-sm tracking-widest">YOUR LOCAL MEDIA LIBRARY</p>
          <h1 className="text-3xl font-semibold text-white mt-2">Welcome, {user.username}</h1>
          <p className="text-white/60 mt-2">Your videos. Your progress. Ready when you are.</p>
        </header>
        {error && <div role="alert" className="p-4 rounded-xl bg-red-950/60 text-red-200">{error}
          <button className="ml-4 underline" onClick={() => { fetchCatalog(); fetchDashboard(); fetchTrending(); }}>Retry</button>
        </div>}

        {dashboard.length > 0 && (
          <section id="dashboard">
            <div className="flex items-center space-x-3 mb-6">
              <motion.div
                whileHover={{ y: -1 }}
                className="p-2 rounded-xl bg-accent/15 border border-accent/20"
              >
                <Play size={18} className="text-accent" />
              </motion.div>
              <h2 className="text-2xl font-semibold text-white/95 tracking-tight">Continue Watching</h2>
            </div>
            <div className="flex overflow-x-auto space-x-6 pt-4 pb-6 px-2 -mx-2 hide-scrollbar snap-x">
              {dashboard.map((item, i) => (
                <MediaCard
                  key={i}
                  media={item}
                  catalog={catalog}
                  isResume={true}
                  onClick={() => setActiveMedia({ ...item, resumeAt: item.last_position })}
                />
              ))}
            </div>
          </section>
        )}

        <section id="trending">
          <div className="flex items-center space-x-3 mb-6">
            <motion.div
              whileHover={{ y: -1 }}
              className="p-2 rounded-xl bg-accent/15 border border-accent/20"
            >
              <Flame size={18} className="text-accent" />
            </motion.div>
            <h2 className="text-2xl font-semibold text-white/95 tracking-tight">Top 10 Trending</h2>
            <span className="text-xs font-bold text-accent bg-accent/10 border border-accent/20 px-2.5 py-1 rounded-full ">WATCH HISTORY</span>
          </div>
          <div className="flex overflow-x-auto space-x-6 pt-4 pb-6 px-2 -mx-2 hide-scrollbar snap-x">
            {trending.map((item, i) => (
              <MediaCard
                key={i}
                media={item}
                catalog={catalog}
                rank={i + 1}
                onClick={() => openEntry(item)}
              />
            ))}
          </div>
        </section>

        <section id="catalog">
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 space-y-4 md:space-y-0">
            <div className="flex items-center space-x-3">
              <motion.div
                whileHover={{ y: -1 }}
                className="p-2 rounded-xl bg-accent/15 border border-accent/20"
              >
                <Film size={18} className="text-accent" />
              </motion.div>
              <h2 className="text-2xl font-semibold text-white/95 tracking-tight">Catalog</h2>
              <span className="text-xs font-medium text-white/60 bg-white/10 backdrop-blur-lg px-2.5 py-1 rounded-full border border-white/10">{filteredCatalog.length} loaded</span>
            </div>
            <div className="flex space-x-3">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 group-focus-within:text-accent transition-colors" size={16} />
                <input
                  type="text"
                  placeholder="Search title words..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-white/10 backdrop-blur-lg border border-white/10 rounded-full text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 text-white backdrop-blur-md w-64 transition-colors"
                />
              </div>
              <select
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                className="bg-white/10 backdrop-blur-lg border border-white/10 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-accent/50 cursor-pointer text-white backdrop-blur-md appearance-none"
              >
                <option value="" className="bg-white/5 backdrop-blur-md">All Genres</option>
                {Array.from(genres).map(g => (
                  <option key={g} value={g} className="bg-white/5 backdrop-blur-md">{g}</option>
                ))}
              </select>
            </div>
          </div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ staggerChildren: 0.05 }}
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6"
          >
            {filteredCatalog.map(item => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 8, scale: 1 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.22 }}
              >
                <MediaCard
                  media={item}
                  catalog={catalog}
                  fullWidth
                  onClick={() => openEntry(item)}
                />
              </motion.div>
            ))}
          </motion.div>
          {loading && <p className="mt-6 text-white/60" role="status">Loading library…</p>}
          {!loading && catalog.length === 0 && <p className="mt-6 text-white/60">
            {searchQuery || selectedGenre ? 'No videos match your search.' :
              user.is_admin ? 'Your library is empty. Use Add Media to add your first video.' : 'Your library is empty. Ask the administrator to add videos.'}
          </p>}
          {nextCursor !== null && <button disabled={loading}
            onClick={() => fetchCatalog(nextCursor)}
            className="mt-8 px-6 py-3 rounded-full bg-accent-strong text-white disabled:opacity-50">
            Load more
          </button>}
        </section>
      </main>

      {/* Modals */}
      {activeSeries && !activeMedia && <SeriesModal media={activeSeries} user={user}
        onPlay={episode => setActiveMedia(episode)}
        onClose={() => { setActiveSeries(null); fetchCatalog(); fetchDashboard(); fetchTrending(); }} />}

      <AnimatePresence>
        {activeMedia && (
          <PlayerModal
            media={activeMedia}
            onClose={() => {
              setActiveMedia(null);
              fetchCatalog();
              setPlayerIsPlaying(false);
              setPlayerPosition(0);
              if (currentUser) {
                fetchDashboard(currentUser);
                fetchTrending();
              }
            }}
            currentUser={currentUser}
            user={user}
            onDelete={() => {
              fetchCatalog();
              fetchTrending();
              if (currentUser) fetchDashboard(currentUser);
            }}
            isPlaying={playerIsPlaying}
            setIsPlaying={setPlayerIsPlaying}
            position={playerPosition}
            setPosition={setPlayerPosition}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showAddModal && (
          <AddMediaModal
            isOpen={showAddModal}
            onClose={() => setShowAddModal(false)}
            onSuccess={() => fetchCatalog()}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function MediaCard({ media, catalog, isResume, onClick, fullWidth, rank }) {
  const fullMedia = isResume ? media : catalog.find(c => c.id === (media.media_id || media.id)) || media;

  const genreStyle = getGenreStyle(fullMedia.genre);

  const bgStyle = fullMedia.poster_path
    ? `url('https://image.tmdb.org/t/p/w500${fullMedia.poster_path}')`
    : 'linear-gradient(145deg, #223d3b, #141c22 75%)';

  return (
    <motion.div
      whileHover={{ y: -8, scale: 1.035 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 340, damping: 27, mass: 0.7 }}
      onClick={onClick}
      role="button" tabIndex={0} aria-label={'Open ' + (fullMedia.title || fullMedia.media_title)}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
      className={`glass-panel rounded-2xl overflow-hidden cursor-pointer snap-start flex flex-col group media-card transition-shadow duration-300 ${fullWidth ? 'w-full' : 'w-48 sm:w-56 flex-none'}`}
    >
      <div className="aspect-[2/3] w-full relative overflow-hidden">
        <div className="media-card-poster absolute inset-0 bg-cover bg-center" style={{ backgroundImage: bgStyle }} />
        <div className="media-card-action absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 pointer-events-none" aria-hidden="true">
          <span className="media-card-play"><Play size={25} fill="currentColor" strokeWidth={1.5} /></span>
          <span className="media-card-action-label">{fullMedia.media_type === 'tv' ? 'View episodes' : isResume ? 'Continue watching' : 'Open movie'}</span>
        </div>
        {!fullMedia.poster_path && <Film aria-hidden="true" size={44} className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-accent/40" />}
        <div className="absolute inset-0 bg-gradient-to-t from-canvas/90 via-canvas/20 to-transparent opacity-60 group-hover:opacity-30 transition-opacity duration-300"></div>

        {/* Premium Netflix-style Rank badge for trending */}
        {rank && (
          <div className="absolute -left-3 bottom-8 flex items-end drop-shadow-2xl z-20 pointer-events-none">
            <span
              className="text-8xl font-black italic tracking-tighter"
              style={{
                WebkitTextStroke: `3px rgba(255,255,255,0.9)`,
                color: 'rgba(0,0,0,0.4)',
                textShadow: `0 10px 30px rgba(0,0,0,0.8)`
              }}
            >
              {rank}
            </span>
          </div>
        )}

        {isResume && (
          <div className="absolute bottom-0 left-0 right-0 h-1.5 bg-white/10 backdrop-blur-lg backdrop-blur-sm overflow-hidden">
            <div className="h-full progress-gradient " style={{ width: `${Math.min(100, (media.last_position / (fullMedia.duration || fullMedia.total_duration || 1)) * 100)}%` }}></div>
          </div>
        )}

        <div className="absolute bottom-3 right-3 bg-white/10 backdrop-blur-lg backdrop-blur-md px-2 py-1 rounded-md text-xs font-medium border border-white/10">
          {fullMedia.item_kind === 'series'
            ? fullMedia.season_count + ' season' + (fullMedia.season_count === 1 ? '' : 's')
            : formatTime(fullMedia.total_duration || fullMedia.duration)}
        </div>
      </div>
      <div className="p-4 bg-gradient-to-b from-transparent to-black/50">
        <h3 className="text-sm font-semibold truncate text-white/95">{fullMedia.title || fullMedia.media_title || 'Unknown Title'}</h3>
        {fullMedia.tmdb_rating != null && <p className="flex items-center gap-1.5 text-xs text-accent-soft mt-2"><Star size={13} aria-hidden="true" /> {Number(fullMedia.tmdb_rating).toFixed(1)} / 10</p>}
        {fullMedia.media_type && <p className="text-xs text-accent-soft mt-2">
          {fullMedia.media_type === 'tv' ? 'Series' : 'Movie'}
          {fullMedia.item_kind === 'series' ? ' · ' + fullMedia.episode_count + ' episodes' :
            fullMedia.season_number != null ? ' · S' + fullMedia.season_number : ''}
          {fullMedia.item_kind !== 'series' && fullMedia.episode_number != null ? ' E' + fullMedia.episode_number : ''}
        </p>}
        {['pending', 'preparing'].includes(fullMedia.playback_status) && <p className="text-xs text-amber-200 mt-2">
          {fullMedia.playback_status === 'pending' ? 'Queued for playback preparation' :
            'Preparing full video · ' + Math.floor(fullMedia.prepare_progress || 0) + '%'}
        </p>}
        {['failed', 'cancelled'].includes(fullMedia.playback_status) && <p className="text-xs text-red-300 mt-2">
          {fullMedia.playback_status === 'failed' ? 'Preparation failed · open to retry' : 'Preparation cancelled · open to retry'}
        </p>}
        {fullMedia.genre && (
          <span className={`inline-block text-[10px] font-semibold mt-1.5 px-2 py-0.5 rounded-full border ${genreStyle.bg} ${genreStyle.text} ${genreStyle.border}`}>
            {fullMedia.genre}
          </span>
        )}
        {isResume && media.last_position && <p className="text-xs text-accent mt-1.5 font-medium">{Math.floor(media.last_position / 60)} min completed</p>}
        {!isResume && media.view_count && (
          <div className="flex items-center space-x-1 mt-1.5">
            <TrendingUp size={10} className="text-accent" />
            <p className="text-xs text-white/60">{media.view_count} views</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
