import React, { useState, useEffect } from 'react';
import { AlertCircle, Loader, Download, Play, Calendar, Clock, Users, FileVideo } from 'lucide-react';
import { scriptService } from '../services/scriptService';

function EpisodesPanel() {
  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Fetch completed episodes on component mount
  useEffect(() => {
    fetchEpisodes();
  }, []);
  
  const fetchEpisodes = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch scripts with status "complete"
      const data = await scriptService.getScripts('complete');
      setEpisodes(data);
    } catch (err) {
      console.error('Failed to fetch episodes:', err);
      setError('Failed to load episodes. Please check if the script service is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (scriptId, title) => {
    const downloadUrl = `http://localhost:8005/stitch/download/${scriptId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}_episode.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePreview = (scriptId) => {
    const videoUrl = `http://localhost:8005/stitch/download/${scriptId}`;
    window.open(videoUrl, '_blank');
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getEpisodeStats = (episode) => {
    // Calculate estimated video duration (assuming ~1 minute per script minute)
    const estimatedDuration = episode.length_minutes || 0;
    return {
      duration: estimatedDuration,
      lines: episode.total_lines || 0
    };
  };
  
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>🎬 Completed Episodes</h2>
        <button onClick={fetchEpisodes} className="btn-secondary" disabled={loading}>
          {loading ? <Loader className="spin" size={16} /> : 'Refresh'}
        </button>
      </div>
      
      <div className="card">
        {loading && (
          <div className="loading-container">
            <Loader className="spin" size={32} />
            <p>Loading episodes...</p>
          </div>
        )}
        
        {error && (
          <div className="alert alert-error">
            <AlertCircle size={20} />
            {error}
          </div>
        )}
        
        {!loading && !error && episodes.length === 0 && (
          <div className="empty-state">
            <FileVideo size={48} className="empty-icon" />
            <h3>No Episodes Yet</h3>
            <p>Completed episodes will appear here when video stitching is complete.</p>
            <p className="text-muted">Create and process scripts to generate your first episode!</p>
          </div>
        )}
        
        {!loading && !error && episodes.length > 0 && (
          <div className="episodes-grid">
            {episodes.map(episode => {
              const stats = getEpisodeStats(episode);
              return (
                <div key={episode.script_id} className="episode-card">
                  <div className="episode-header">
                    <h3 className="episode-title">{episode.title}</h3>
                    <span className="episode-id">#{episode.script_id}</span>
                  </div>
                  
                  <div className="episode-meta">
                    <div className="meta-item">
                      <Clock size={16} />
                      <span>{episode.length_minutes} min</span>
                    </div>
                    <div className="meta-item">
                      <Users size={16} />
                      <span>{episode.format_type || 'Podcast'}</span>
                    </div>
                    <div className="meta-item">
                      <Calendar size={16} />
                      <span>{formatDate(episode.created_at)}</span>
                    </div>
                  </div>

                  <div className="episode-description">
                    <p className="text-muted">
                      {episode.description || `A ${stats.duration}-minute episode featuring ${stats.lines} dialogue segments.`}
                    </p>
                  </div>
                  
                  <div className="episode-actions">
                    <button 
                      onClick={() => handleDownload(episode.script_id, episode.title)}
                      className="btn-success btn-small"
                      title="Download Episode"
                    >
                      <Download size={16} />
                      Download
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default EpisodesPanel; 