import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Plus, Play, X, Star, Trash2, CheckCircle2 } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000/api';

const formatTime = (seconds) => {
  if (!seconds) return '0:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

export default function App() {
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState('');
  const [dashboard, setDashboard] = useState([]);
  const [trending, setTrending] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [genres, setGenres] = useState(new Set());
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('');
  
  const [activeMedia, setActiveMedia] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    fetchUsers();
    fetchCatalog();
    fetchTrending();
  }, []);

  useEffect(() => {
    if (currentUser) {
      fetchDashboard(currentUser);
    } else {
      setDashboard([]);
    }
  }, [currentUser]);

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/users`);
      const data = await res.json();
      setUsers(data);
      if (data.length > 0) setCurrentUser(data[0].id.toString());
    } catch (e) { console.error(e); }
  };

  const fetchCatalog = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/catalog`);
      const data = await res.json();
      setCatalog(data);
      const newGenres = new Set();
      data.forEach(item => { if (item.genre) newGenres.add(item.genre); });
      setGenres(newGenres);
    } catch (e) { console.error(e); }
  };

  const fetchTrending = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/trending`);
      setTrending(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchDashboard = async (userId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/dashboard?user_id=${userId}`);
      setDashboard(await res.json());
    } catch (e) { console.error(e); }
  };

  const filteredCatalog = catalog.filter(item => {
    const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesGenre = selectedGenre === '' || item.genre === selectedGenre;
    return matchesSearch && matchesGenre;
  });

  return (
    <div className="min-h-screen pb-12 flex flex-col relative overflow-hidden">
      {/* Navbar */}
      <motion.header 
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 28 }}
        className="fixed top-0 w-full z-50 glass border-b-0"
      >
        <div className="px-6 py-4 flex items-center justify-between">
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            whileHover={{ scale: 1.05, transition: { duration: 0.15 } }}
            className="text-3xl font-extrabold text-white tracking-widest drop-shadow-lg cursor-pointer select-none"
            style={{ fontFamily: "'Gentium Book Plus', serif" }}
          >
            STREAM
          </motion.div>
          <div className="flex items-center space-x-6">
            <nav className="hidden md:flex space-x-6 items-center font-medium">
              <a href="#dashboard" className="text-white/70 hover:text-white transition-colors">Home</a>
              <a href="#trending" className="text-white/70 hover:text-white transition-colors">Trending</a>
              <a href="#catalog" className="text-white/70 hover:text-white transition-colors">Catalog</a>
              <motion.button 
                onClick={() => setShowAddModal(true)}
                whileHover={{ scale: 1.05, backgroundColor: 'rgba(255,255,255,0.2)' }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center space-x-1 bg-white/10 text-white text-sm py-1.5 px-4 rounded-full border border-white/10"
              >
                <Plus size={16} />
                <span>Add Media</span>
              </motion.button>
            </nav>
            <div className="relative">
              <UserDropdown 
                users={users} 
                currentUser={currentUser} 
                setCurrentUser={setCurrentUser} 
                fetchUsers={fetchUsers}
              />
            </div>
          </div>
        </div>
      </motion.header>

      <main className="flex-grow pt-28 px-6 lg:px-12 space-y-16 relative z-10">
        
        {dashboard.length > 0 && (
          <section id="dashboard">
            <h2 className="text-2xl font-semibold mb-6 text-white/90 tracking-tight">Continue Watching</h2>
            <div className="flex overflow-x-auto space-x-6 pt-4 pb-6 px-2 -mx-2 hide-scrollbar snap-x">
              {dashboard.map((item, i) => (
                <MediaCard 
                  key={i} 
                  media={item} 
                  catalog={catalog} 
                  isResume={true} 
                  onClick={() => setActiveMedia({ ...catalog.find(c => c.id === (item.media_id || item.id)), resumeAt: item.last_position })}
                />
              ))}
            </div>
          </section>
        )}

        <section id="trending">
          <h2 className="text-2xl font-semibold mb-6 text-white/90 tracking-tight">Top 10 Trending</h2>
          <div className="flex overflow-x-auto space-x-6 pt-4 pb-6 px-2 -mx-2 hide-scrollbar snap-x">
            {trending.map((item, i) => (
              <MediaCard 
                key={i} 
                media={item} 
                catalog={catalog} 
                onClick={() => setActiveMedia(catalog.find(c => c.id === (item.media_id || item.id)) || item)}
              />
            ))}
          </div>
        </section>

        <section id="catalog">
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 space-y-4 md:space-y-0">
            <h2 className="text-2xl font-semibold text-white/90 tracking-tight">Catalog</h2>
            <div className="flex space-x-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/50" size={16} />
                <input 
                  type="text" 
                  placeholder="Search title..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-black/40 border border-white/10 rounded-full text-sm focus:outline-none focus:border-accent text-white backdrop-blur-md w-64 transition-all focus:w-72"
                />
              </div>
              <select 
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                className="bg-black/40 border border-white/10 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-accent cursor-pointer text-white backdrop-blur-md appearance-none"
              >
                <option value="" className="bg-darkBg">All Genres</option>
                {Array.from(genres).map(g => (
                  <option key={g} value={g} className="bg-darkBg">{g}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
            {filteredCatalog.map(item => (
              <MediaCard 
                key={item.id} 
                media={item} 
                catalog={catalog} 
                fullWidth
                onClick={() => setActiveMedia(item)}
              />
            ))}
          </div>
        </section>
      </main>

      {/* Modals */}
      <AnimatePresence>
        {activeMedia && (
          <PlayerModal 
            media={activeMedia} 
            onClose={() => {
              setActiveMedia(null);
              if (currentUser) {
                fetchDashboard(currentUser);
                fetchTrending();
              }
            }} 
            currentUser={currentUser}
            onDelete={() => {
              fetchCatalog();
              fetchTrending();
              if (currentUser) fetchDashboard(currentUser);
            }}
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

function MediaCard({ media, catalog, isResume, onClick, fullWidth }) {
  const fullMedia = catalog.find(c => c.id === (media.media_id || media.id)) || media;
  const bgStyle = fullMedia.poster_path 
    ? `url('https://image.tmdb.org/t/p/w500${fullMedia.poster_path}')`
    : `linear-gradient(135deg, hsl(${((fullMedia.id || 1) * 137) % 360}, 40%, 30%), hsl(${((fullMedia.id || 1) * 137) % 360}, 60%, 15%))`;

  return (
    <motion.div 
      whileHover={{ scale: 1.03, y: -4 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'tween', duration: 0.15, ease: 'easeOut' }}
      onClick={onClick}
      className={`glass-panel rounded-2xl overflow-hidden cursor-pointer snap-start flex flex-col group ${fullWidth ? 'w-full' : 'w-48 sm:w-56 flex-none'}`}
    >
      <div className="aspect-[2/3] w-full relative bg-cover bg-center" style={{ backgroundImage: bgStyle }}>
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-60 group-hover:opacity-40 transition-opacity"></div>
        
        {isResume && (
          <div className="absolute bottom-0 left-0 right-0 h-1.5 bg-white/20 backdrop-blur-sm overflow-hidden">
            <div className="h-full bg-accent shadow-[0_0_10px_rgba(229,9,20,0.8)]" style={{ width: `${Math.min(100, (media.last_position / (fullMedia.duration || fullMedia.total_duration || 1)) * 100)}%` }}></div>
          </div>
        )}
        
        <div className="absolute bottom-3 right-3 bg-black/60 backdrop-blur-md px-2 py-1 rounded-md text-xs font-medium border border-white/10">
          {formatTime(fullMedia.total_duration || fullMedia.duration)}
        </div>
      </div>
      <div className="p-4 bg-gradient-to-b from-transparent to-black/50">
        <h3 className="text-sm font-semibold truncate text-white/95">{fullMedia.title || fullMedia.media_title || 'Unknown Title'}</h3>
        {fullMedia.genre && <p className="text-xs text-white/50 mt-1">{fullMedia.genre}</p>}
        {isResume && media.last_position && <p className="text-xs text-accent mt-1 font-medium">{Math.floor(media.last_position / 60)} minutes completed</p>}
        {!isResume && media.view_count && <p className="text-xs text-white/40 mt-1">{media.view_count} views</p>}
      </div>
    </motion.div>
  );
}

function PlayerModal({ media, onClose, currentUser, onDelete }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [position, setPosition] = useState(0);

  useEffect(() => {
    if (media) {
      setPosition(media.resumeAt || 0);
      document.body.style.overflow = 'hidden';
    } else {
      setIsPlaying(false);
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [media]);

  useEffect(() => {
    let interval;
    if (isPlaying && media) {
      const duration = media.duration || media.total_duration;
      interval = setInterval(() => {
        setPosition(p => {
          if (p >= duration) {
            setIsPlaying(false);
            return duration;
          }
          const newPos = p + 1;
          if (newPos % 5 === 0) sendHeartbeat(newPos);
          return newPos;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, media, currentUser]);

  const sendHeartbeat = async (pos) => {
    if (!currentUser || !media) return;
    try {
      await fetch(`${API_BASE_URL}/playback/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: parseInt(currentUser),
          media_id: media.id,
          position_seconds: pos
        })
      });
    } catch (e) { console.error(e); }
  };

  const handleFinish = async () => {
    if (!currentUser || !media) return;
    try {
      await fetch(`${API_BASE_URL}/playback/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: parseInt(currentUser),
          media_id: media.id
        })
      });
      onClose();
    } catch (e) { console.error(e); }
  };

  const handleDelete = async () => {
    if (!media) return;
    if (!confirm("Are you sure you want to completely delete this movie?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/catalog/${media.id}`, { method: 'DELETE' });
      if (res.ok) {
        onDelete();
        onClose();
      }
    } catch (e) { console.error(e); }
  };

  if (!media) return null;

  const duration = media.duration || media.total_duration;
  const progress = (position / duration) * 100;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-md"
        onClick={() => {
          if (position > 0) sendHeartbeat(position);
          onClose();
        }}
      />
      <motion.div 
        initial={{ scale: 0.95, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0, y: 10 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className="relative w-full max-w-4xl glass rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div 
          className="h-64 sm:h-80 relative bg-cover bg-center shrink-0"
          style={{ backgroundImage: media.backdrop_path ? `url('https://image.tmdb.org/t/p/w1280${media.backdrop_path}')` : 'none', backgroundColor: '#111' }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-darkBg via-darkBg/60 to-transparent" />
          <button 
            onClick={() => { if(position > 0) sendHeartbeat(position); onClose(); }}
            className="absolute top-6 right-6 bg-black/40 hover:bg-white/20 p-2 rounded-full backdrop-blur-md transition-all text-white/80 hover:text-white"
          >
            <X size={24} />
          </button>
          
          <div className="absolute bottom-6 left-8 right-8">
            <h2 className="text-4xl sm:text-5xl font-extrabold text-white drop-shadow-xl tracking-tight mb-2">{media.title || media.media_title}</h2>
            <div className="flex items-center space-x-3 text-sm text-white/70 font-medium">
              <span>{formatTime(duration)}</span>
              <span>•</span>
              <span>{media.genre || 'Unknown Genre'}</span>
              {media.tmdb_rating && (
                <>
                  <span>•</span>
                  <span className="flex items-center text-yellow-400"><Star size={14} className="mr-1 fill-current" /> {parseFloat(media.tmdb_rating).toFixed(1)}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-8 space-y-8 overflow-y-auto hide-scrollbar">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="md:col-span-2 space-y-4">
              {media.overview && <p className="text-white/80 text-sm leading-relaxed">{media.overview}</p>}
              <div className="text-sm text-white/60 space-y-1">
                <p><strong className="text-white/90">Cast:</strong> {media.actors?.length ? media.actors.join(', ') : 'Unknown'}</p>
                <p><strong className="text-white/90">Studio:</strong> {media.studio || 'Unknown'}</p>
              </div>
            </div>
          </div>

          {/* Player Controls */}
          <div className="glass-panel p-6 rounded-2xl space-y-6 border border-white/10">
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-white/60 font-medium font-mono">
                <span>{formatTime(position)}</span>
                <span>{formatTime(duration)}</span>
              </div>
              <div className="relative h-2 bg-white/10 rounded-full overflow-hidden cursor-pointer">
                <input 
                  type="range" 
                  min="0" 
                  max={duration} 
                  value={position}
                  onChange={(e) => {
                    setPosition(Number(e.target.value));
                    sendHeartbeat(Number(e.target.value));
                  }}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <div 
                  className="h-full bg-accent rounded-full transition-[width] duration-300 ease-linear"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
              <motion.button 
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setIsPlaying(!isPlaying)}
                className="bg-white text-black px-8 py-3 rounded-full font-bold hover:bg-white/90 transition-colors flex items-center space-x-2 w-full sm:w-auto justify-center"
              >
                {isPlaying ? <X size={20} /> : <Play size={20} className="fill-current" />}
                <span>{isPlaying ? 'Pause' : 'Play'}</span>
              </motion.button>
              
              <div className="flex space-x-3 w-full sm:w-auto">
                <button 
                  onClick={handleDelete}
                  className="flex-1 sm:flex-none flex items-center justify-center space-x-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 px-6 py-3 rounded-full font-semibold transition-colors text-sm"
                >
                  <Trash2 size={16} />
                  <span>Delete</span>
                </button>
                <button 
                  onClick={handleFinish}
                  className="flex-1 sm:flex-none flex items-center justify-center space-x-2 bg-accent hover:bg-red-700 text-white px-6 py-3 rounded-full font-semibold transition-colors text-sm shadow-[0_0_15px_rgba(229,9,20,0.4)]"
                >
                  <CheckCircle2 size={16} />
                  <span>Finish</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function AddMediaModal({ isOpen, onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [path, setPath] = useState('');
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', msg: string }
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const res = await fetch(`${API_BASE_URL}/catalog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, path })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setStatus({ type: 'success', msg: `Added "${data.title}" successfully!` });
        onSuccess();
        setTimeout(() => {
          onClose();
          setTitle('');
          setPath('');
          setStatus(null);
        }, 1500);
      } else {
        setStatus({ type: 'error', msg: data.detail || 'Failed to add media' });
      }
    } catch (err) {
      setStatus({ type: 'error', msg: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-md"
        onClick={onClose}
      />
      <motion.div 
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className="relative w-full max-w-md glass rounded-3xl p-8 shadow-2xl border border-white/10"
      >
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white tracking-tight">Add New Media</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white transition-colors bg-white/5 hover:bg-white/10 p-2 rounded-full">
            <X size={20} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">Movie/TV Title <span className="text-white/40 font-normal">(Optional)</span></label>
            <input 
              type="text" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Leave blank to extract from filename" 
              className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-accent focus:bg-black/50 transition-all backdrop-blur-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">File Path</label>
            <input 
              type="text" 
              value={path}
              onChange={(e) => setPath(e.target.value)}
              required 
              placeholder="e.g. /media/movies/matrix.mp4" 
              className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-accent focus:bg-black/50 transition-all backdrop-blur-sm"
            />
          </div>
          
          <motion.button 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit" 
            disabled={loading}
            className="w-full bg-accent text-white font-bold py-3 rounded-xl hover:bg-red-700 transition-colors mt-2 shadow-[0_0_15px_rgba(229,9,20,0.3)] disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Media'}
          </motion.button>
          
          {status && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`text-sm text-center p-3 rounded-lg font-medium border ${status.type === 'success' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}
            >
              {status.msg}
            </motion.div>
          )}
        </form>
      </motion.div>
    </motion.div>
  );
}

function UserDropdown({ users, currentUser, setCurrentUser, fetchUsers }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  
  const current = users.find(u => u.id.toString() === currentUser);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newUsername.trim()) return;
    try {
      const res = await fetch(`${API_BASE_URL}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername })
      });
      if (res.ok) {
        const data = await res.json();
        await fetchUsers();
        setCurrentUser(data.id.toString());
        setNewUsername('');
        setIsAdding(false);
        setIsOpen(false);
      }
    } catch (err) { console.error(err); }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Delete this user?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/users/${id}`, { method: 'DELETE' });
      if (res.ok) {
        if (currentUser === id.toString()) setCurrentUser('');
        await fetchUsers();
      }
    } catch (err) { console.error(err); }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 bg-black/40 border border-white/10 text-sm rounded-full px-4 py-2 hover:bg-black/60 focus:outline-none transition-colors text-white backdrop-blur-md min-w-[140px] justify-between"
      >
        <span className="truncate font-medium">{current ? current.username : 'Select User'}</span>
        <svg className={`w-4 h-4 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
      </button>

      {isOpen && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute right-0 mt-2 w-56 bg-[#1a1a1a] rounded-2xl overflow-hidden shadow-2xl border border-white/20 z-50 flex flex-col"
        >
          <div className="max-h-60 overflow-y-auto hide-scrollbar py-2">
            {users.map(u => (
              <div 
                key={u.id}
                onClick={() => { setCurrentUser(u.id.toString()); setIsOpen(false); }}
                className={`flex items-center justify-between px-4 py-2 cursor-pointer transition-colors group ${currentUser === u.id.toString() ? 'bg-accent/20 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}
              >
                <span className="truncate font-medium text-sm">{u.username}</span>
                <button onClick={(e) => handleDelete(e, u.id)} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 rounded hover:bg-red-500/20 transition-all flex-shrink-0">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
          
          <div className="border-t border-white/10 p-2 bg-black/20">
            {isAdding ? (
              <form onSubmit={handleAdd} className="flex flex-col space-y-2">
                <input 
                  type="text" 
                  autoFocus
                  placeholder="Username..." 
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent w-full backdrop-blur-sm"
                />
                <div className="flex space-x-2">
                  <button type="submit" className="flex-1 bg-accent text-white text-xs font-bold py-2 rounded-lg hover:bg-red-700 transition-colors shadow-lg">Add</button>
                  <button type="button" onClick={() => setIsAdding(false)} className="flex-1 bg-white/10 text-white text-xs font-bold py-2 rounded-lg hover:bg-white/20 transition-colors">Cancel</button>
                </div>
              </form>
            ) : (
              <button 
                onClick={() => setIsAdding(true)}
                className="w-full flex items-center justify-center space-x-1 text-sm font-semibold text-white/90 hover:text-white bg-white/5 hover:bg-white/15 py-2 rounded-xl transition-all border border-white/5 hover:border-white/20"
              >
                <Plus size={14} />
                <span>New User</span>
              </button>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
