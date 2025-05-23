import React, { useState, useRef, useEffect } from 'react';
import { Edit3, Check, X, Play, Pause, RotateCcw, Volume2, Video, ExternalLink } from 'lucide-react';
import { getSpeakerColor } from '../utils/formatUtils';
import { scriptService } from '../services/scriptService';
import { API_CONFIG } from '../config';

function ScriptLine({ line, index, isEditing, onEdit, onSave, onCancel, onStatusUpdate }) {
  const [editText, setEditText] = useState(line.text);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [ttsStatus, setTtsStatus] = useState(line.tts_status || 'pending');
  const [isRegeneratingFrame, setIsRegeneratingFrame] = useState(false);
  const [frameStatus, setFrameStatus] = useState(line.avatar_status || 'pending');
  const audioRef = useRef(null);

  useEffect(() => {
    setTtsStatus(line.tts_status || 'pending');
    setFrameStatus(line.avatar_status || 'pending');
  }, [line.tts_status, line.avatar_status]);

  const handleSave = () => {
    if (editText.trim() !== line.text) {
      onSave(editText);
    } else {
      onCancel();
    }
  };

  const handlePlayPause = async () => {
    if (!audioRef.current) {
      // Get the audio URL - this will handle the redirect
      const audioUrl = scriptService.getAudioUrl(line.line_id);
      audioRef.current = new Audio(audioUrl);
      
      audioRef.current.addEventListener('ended', () => setIsPlaying(false));
      audioRef.current.addEventListener('error', (e) => {
        setIsPlaying(false);
        console.error('Audio playback error:', e);
        alert('Error playing audio file. Please check if TTS was successful.');
      });

      // Add load event listener to handle redirects better
      audioRef.current.addEventListener('loadstart', () => {
        console.log('Audio loading started');
      });
      audioRef.current.addEventListener('canplay', () => {
        console.log('Audio can play');
      });
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      try {
        await audioRef.current.play();
        setIsPlaying(true);
      } catch (error) {
        console.error('Failed to play audio:', error);
        setIsPlaying(false);
        alert('Failed to play audio. The file might not be ready yet.');
      }
    }
  };

  const handleRegenerateTTS = async () => {
    setIsRegenerating(true);
    try {
      await scriptService.processSingleLineTTS(line.line_id);
      setTtsStatus('processing');
      
      // Poll for completion
      const pollStatus = async () => {
        try {
          const status = await scriptService.getLineTTSStatus(line.line_id);
          setTtsStatus(status.tts_status);
          
          if (status.tts_status === 'processing') {
            setTimeout(pollStatus, 2000); // Poll every 2 seconds
          } else {
            // Notify parent to refresh data
            if (onStatusUpdate) onStatusUpdate();
          }
        } catch (error) {
          console.error('Error polling TTS status:', error);
        }
      };
      
      setTimeout(pollStatus, 2000);
    } catch (error) {
      console.error('Error regenerating TTS:', error);
      alert(`Failed to regenerate TTS: ${error.message}`);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleRegenerateFrame = async () => {
    setIsRegeneratingFrame(true);
    try {
      await scriptService.processSingleLineFrame(line.line_id);
      setFrameStatus('processing');
      
      // Start polling for completion with better error handling
      startFrameStatusPolling();
    } catch (error) {
      console.error('Error regenerating frame:', error);
      alert(`Failed to regenerate frame: ${error.message}`);
      // Don't change the frame status on API error - keep current status
    } finally {
      setIsRegeneratingFrame(false);
    }
  };

  // Separate polling function with better error handling
  const startFrameStatusPolling = () => {
    const pollInterval = 5000; // 5 seconds
    let pollAttempts = 0;
    const maxPollAttempts = 60; // Max 5 minutes of polling
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 3;

    const pollFrameStatus = async () => {
      try {
        const status = await scriptService.getLineFrameStatus(line.line_id);
        consecutiveErrors = 0; // Reset error count on success
        setFrameStatus(status.status);
        
        if (status.status === 'processing' && pollAttempts < maxPollAttempts) {
          pollAttempts++;
          setTimeout(pollFrameStatus, pollInterval);
        } else {
          // Notify parent to refresh data when complete or max attempts reached
          if (onStatusUpdate) onStatusUpdate();
          
          if (pollAttempts >= maxPollAttempts && status.status === 'processing') {
            console.warn(`Polling timeout for line ${line.line_id} after ${maxPollAttempts} attempts`);
            // Try to sync stuck job
            tryToSyncStuckJob();
          }
        }
      } catch (error) {
        console.error('Error polling frame status:', error);
        pollAttempts++;
        consecutiveErrors++;
        
        // If too many consecutive errors, stop polling
        if (consecutiveErrors >= maxConsecutiveErrors) {
          console.error(`Too many consecutive errors for line ${line.line_id}, stopping polling`);
          // Try to sync stuck job as a fallback
          tryToSyncStuckJob();
          return;
        }
        
        // Continue polling on error up to max attempts (network issues might be temporary)
        if (pollAttempts < maxPollAttempts) {
          setTimeout(pollFrameStatus, pollInterval * Math.pow(2, consecutiveErrors)); // Exponential backoff
        } else {
          console.error(`Max polling attempts reached for line ${line.line_id}`);
          // Try to sync stuck job as a fallback
          tryToSyncStuckJob();
        }
      }
    };

    // Start polling after initial delay
    setTimeout(pollFrameStatus, pollInterval);
  };

  // Helper function to try syncing stuck jobs
  const tryToSyncStuckJob = async () => {
    try {
      console.log(`Attempting to sync potentially stuck job for line ${line.line_id}`);
      const response = await fetch(`${API_CONFIG.AVATAR_SERVICE}/avatar/sync-stuck-jobs`, {
        method: 'POST'
      });
      
      if (response.ok) {
        console.log('Sync request successful, refreshing status');
        // Wait a moment then refresh
        setTimeout(() => {
          if (onStatusUpdate) onStatusUpdate();
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to sync stuck job:', error);
    }
  };

  const handleOpenVideo = async () => {
    try {
      const videoUrl = scriptService.getVideoUrl(line.line_id);
      // Test if the video URL is accessible before opening
      const response = await fetch(videoUrl, { method: 'HEAD' });
      if (response.ok) {
        window.open(videoUrl, '_blank');
      } else {
        alert('Video file not found or not accessible yet.');
      }
    } catch (error) {
      console.error('Error accessing video:', error);
      alert('Failed to access video file. Please try again later.');
    }
  };

  const getTTSStatusIcon = () => {
    switch (ttsStatus) {
      case 'complete':
        return (
          <div className="status-indicator status-complete" title="TTS Complete - Ready for Frame Generation">
            <Volume2 size={16} />
            <span className="status-label">TTS Complete</span>
          </div>
        );
      case 'processing':
        return (
          <div className="status-indicator status-processing" title="Processing TTS">
            <div className="spinner" />
            <span className="status-label">Processing TTS</span>
          </div>
        );
      case 'failed':
        return (
          <div className="status-indicator status-failed" title="TTS Processing Failed">
            <X size={16} />
            <span className="status-label">TTS Failed</span>
          </div>
        );
      default:
        return (
          <div className="status-indicator status-pending" title="Ready for TTS">
            <div className="pending-dot" />
            <span className="status-label">Ready for TTS</span>
          </div>
        );
    }
  };

  const getFrameStatusIcon = () => {
    // If TTS is not complete, show waiting for TTS
    if (ttsStatus !== 'complete') {
      return (
        <div className="status-indicator status-pending" title="Waiting for TTS">
          <div className="pending-dot" />
          <span className="status-label">Waiting for TTS</span>
        </div>
      );
    }

    // If TTS is complete, show frame status
    switch (frameStatus) {
      case 'complete':
        return (
          <div className="status-indicator status-complete" title="Frame Generation Complete">
            <Video size={16} />
            <span className="status-label">Frame Ready</span>
          </div>
        );
      case 'processing':
        return (
          <div className="status-indicator status-processing" title="Processing Frame">
            <div className="spinner" />
            <span className="status-label">Generating Frame</span>
          </div>
        );
      case 'failed':
        return (
          <div className="status-indicator status-failed" title="Frame Generation Failed">
            <X size={16} />
            <span className="status-label">Frame Failed</span>
          </div>
        );
      case 'ready_for_processing':
        return (
          <div className="status-indicator status-ready" title="Ready for Frame Generation">
            <div className="ready-dot" />
            <span className="status-label">Ready for Frame</span>
          </div>
        );
      default:
        // TTS is complete but frame generation hasn't started yet (pending status)
        return (
          <div className="status-indicator status-ready" title="Ready for Frame Generation">
            <div className="ready-dot" />
            <span className="status-label">Ready for Frame</span>
          </div>
        );
    }
  };

  return (
    <div className="script-line">
      <div className="line-header">
        <div className="speaker-info">
          <span className={`speaker-badge ${getSpeakerColor(line.speaker_role)}`}>
            {line.speaker_name || line.speaker_role}
          </span>
          <span className="line-number">#{index + 1}</span>
        </div>
        <div className="tts-controls">
          <div className="tts-status-container">
            {getTTSStatusIcon()}
          </div>
          <div className="tts-actions">
            {ttsStatus === 'complete' && (
              <button 
                className="btn-icon btn-play"
                onClick={handlePlayPause}
                title={isPlaying ? 'Pause Audio' : 'Play Audio'}
              >
                {isPlaying ? <Pause size={16} /> : <Play size={16} />}
              </button>
            )}
            <button
              className="btn-icon btn-regenerate"
              onClick={handleRegenerateTTS}
              disabled={isRegenerating}
              title="Regenerate TTS"
            >
              {isRegenerating ? <div className="spinner-small" /> : <RotateCcw size={16} />}
            </button>
          </div>
        </div>
        <div className="frame-controls">
          <div className="frame-status-container">
            {getFrameStatusIcon()}
          </div>
          <div className="frame-actions">
            {frameStatus === 'complete' && (
              <button 
                className="btn-icon btn-video"
                onClick={handleOpenVideo}
                title="Open Video"
              >
                <ExternalLink size={16} />
              </button>
            )}
            <button
              className="btn-icon btn-regenerate"
              onClick={handleRegenerateFrame}
              disabled={isRegeneratingFrame || ttsStatus !== 'complete'}
              title={ttsStatus !== 'complete' ? 'Complete TTS first' : 'Generate Frame'}
            >
              {isRegeneratingFrame ? <div className="spinner-small" /> : <Video size={16} />}
            </button>
          </div>
        </div>
        <div className="line-actions">
          {!isEditing ? (
            <button onClick={onEdit} className="btn-icon">
              <Edit3 size={16} />
            </button>
          ) : (
            <div className="edit-actions">
              <button onClick={handleSave} className="btn-icon btn-success">
                <Check size={16} />
              </button>
              <button onClick={onCancel} className="btn-icon btn-danger">
                <X size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="line-content">
        {isEditing ? (
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="line-edit-textarea"
            autoFocus
          />
        ) : (
          <p className="line-text">{line.text}</p>
        )}
      </div>
    </div>
  );
}

export default ScriptLine; 