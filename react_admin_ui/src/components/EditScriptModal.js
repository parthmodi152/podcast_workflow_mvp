import React, { useState, useEffect, useCallback } from 'react';
import { X, Check, AlertCircle, Loader, Download, Video, RotateCcw } from 'lucide-react';
import { scriptService } from '../services/scriptService';
import ScriptLine from './ScriptLine';

function EditScriptModal({ script, onClose, onSuccess }) {
  const [scriptDetails, setScriptDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingLine, setEditingLine] = useState(null);
  const [stitchStatus, setStitchStatus] = useState(null);
  const [isStitching, setIsStitching] = useState(false);
  const [frameGenerationStatus, setFrameGenerationStatus] = useState({
    isProcessing: false,
    failedLines: []
  });

  const fetchScriptDetails = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true);
    }
    setError(null);
    
    try {
      const data = await scriptService.getScript(script.script_id);
      setScriptDetails(data);
      if (!silent) {
        console.log('Script details loaded successfully');
      }
    } catch (err) {
      console.error('Failed to fetch script details:', err);
      setError(`Failed to load script details: ${err.message}`);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [script.script_id]);

  useEffect(() => {
    fetchScriptDetails();
  }, [fetchScriptDetails]);

  const handleSaveEdit = async (lineId, newText) => {
    try {
      // Call the API to update the script line
      await scriptService.updateScriptLine(lineId, newText);
      
      // Update local state after successful API call
      setScriptDetails(prev => ({
        ...prev,
        lines: prev.lines.map(line => 
          line.line_id === lineId ? { ...line, text: newText } : line
        )
      }));
      setEditingLine(null);
      
      console.log(`Script line ${lineId} updated successfully`);
      
    } catch (err) {
      console.error('Failed to save edit:', err);
      setError(`Failed to save changes: ${err.message}`);
    }
  };

  const handleGenerateTTS = async () => {
    try {
      await scriptService.generateTTS(script.script_id);
      alert('TTS generation started successfully!');
      
      // Refresh script details to update statuses
      fetchScriptDetails();
      
    } catch (err) {
      console.error('Failed to generate TTS:', err);
      setError(`Failed to generate TTS: ${err.message}`);
    }
  };

  const getRemainingTTSCount = () => {
    if (!scriptDetails || !scriptDetails.lines) return 0;
    return scriptDetails.lines.filter(line => 
      line.tts_status === 'pending' || line.tts_status === 'failed'
    ).length;
  };

  const getCompletedTTSCount = () => {
    if (!scriptDetails || !scriptDetails.lines) return 0;
    return scriptDetails.lines.filter(line => line.tts_status === 'complete').length;
  };

  const getRemainingFrameCount = () => {
    if (!scriptDetails || !scriptDetails.lines) return 0;
    return scriptDetails.lines.filter(line => 
      line.tts_status === 'complete' && 
      (line.avatar_status === 'pending' || line.avatar_status === 'ready_for_processing' || line.avatar_status === 'failed')
    ).length;
  };

  const getCompletedFrameCount = () => {
    if (!scriptDetails || !scriptDetails.lines) return 0;
    return scriptDetails.lines.filter(line => line.avatar_status === 'complete').length;
  };

  const handleGenerateFrames = async () => {
    const readyLines = scriptDetails.lines.filter(line => 
      line.tts_status === 'complete' && 
      (line.avatar_status === 'pending' || line.avatar_status === 'ready_for_processing' || line.avatar_status === 'failed')
    );

    if (readyLines.length === 0) {
      alert('No lines ready for frame generation');
      return;
    }

    setFrameGenerationStatus({ isProcessing: true, failedLines: [] });

    const results = {
      successful: [],
      failed: []
    };

    // Process each line individually with error handling
    for (const line of readyLines) {
      try {
        await scriptService.processSingleLineFrame(line.line_id);
        results.successful.push(line.line_id);
        console.log(`Frame generation started for line ${line.line_id}`);
      } catch (error) {
        console.error(`Failed to start frame generation for line ${line.line_id}:`, error);
        results.failed.push({ lineId: line.line_id, error: error.message });
      }
    }

    // Update state with results
    setFrameGenerationStatus({ 
      isProcessing: results.successful.length > 0, 
      failedLines: results.failed 
    });

    // Show results to user
    if (results.successful.length > 0 && results.failed.length === 0) {
      alert(`Frame generation started for all ${results.successful.length} lines!`);
    } else if (results.successful.length > 0 && results.failed.length > 0) {
      alert(`Frame generation started for ${results.successful.length} lines. ${results.failed.length} lines failed to start.`);
    } else {
      alert(`Failed to start frame generation for all lines. Please try again.`);
      setFrameGenerationStatus({ isProcessing: false, failedLines: results.failed });
    }

    // Set up polling for successfully submitted lines
    if (results.successful.length > 0) {
      startBulkFramePolling(results.successful);
    }

    // Refresh script details regardless of results
    fetchScriptDetails(true);
  };

  // Retry failed frame generation attempts
  const retryFailedFrameGeneration = async () => {
    const failedLineIds = frameGenerationStatus.failedLines.map(f => f.lineId);
    const linesToRetry = scriptDetails.lines.filter(line => failedLineIds.includes(line.line_id));
    
    setFrameGenerationStatus(prev => ({ ...prev, isProcessing: true }));

    const results = {
      successful: [],
      stillFailed: []
    };

    for (const line of linesToRetry) {
      try {
        await scriptService.processSingleLineFrame(line.line_id);
        results.successful.push(line.line_id);
        console.log(`Retry successful for line ${line.line_id}`);
      } catch (error) {
        console.error(`Retry failed for line ${line.line_id}:`, error);
        results.stillFailed.push({ lineId: line.line_id, error: error.message });
      }
    }

    // Update state
    setFrameGenerationStatus(prev => ({ 
      isProcessing: results.successful.length > 0 || prev.isProcessing, 
      failedLines: results.stillFailed 
    }));

    // Show retry results
    if (results.successful.length > 0) {
      alert(`Retry successful for ${results.successful.length} lines!`);
      if (results.successful.length > 0) {
        startBulkFramePolling(results.successful);
      }
    }

    if (results.stillFailed.length > 0) {
      alert(`${results.stillFailed.length} lines still failed after retry.`);
    }

    fetchScriptDetails(true);
  };

  // Bulk polling function for frame generation
  const startBulkFramePolling = (lineIds) => {
    const pollInterval = 5000; // 5 seconds
    let activePollCount = lineIds.length;

    const pollLineStatus = async (lineId) => {
      try {
        const status = await scriptService.getLineFrameStatus(lineId);
        
        // Check if line is still processing
        if (status.status === 'processing') {
          // Continue polling this line
          setTimeout(() => pollLineStatus(lineId), pollInterval);
        } else {
          // Line completed (success or failure)
          activePollCount--;
          console.log(`Line ${lineId} frame generation completed with status: ${status.status}`);
          
          // Refresh script details when any line completes
          fetchScriptDetails(true);
          
          // If all lines are done, update processing status
          if (activePollCount === 0) {
            console.log('All bulk frame generation jobs completed');
            setFrameGenerationStatus(prev => ({ ...prev, isProcessing: false }));
          }
        }
      } catch (error) {
        console.error(`Error polling frame status for line ${lineId}:`, error);
        activePollCount--;
        
        // Still refresh on error in case other services updated the status
        fetchScriptDetails(true);
        
        // Update processing status if all polling is done
        if (activePollCount === 0) {
          setFrameGenerationStatus(prev => ({ ...prev, isProcessing: false }));
        }
      }
    };

    // Start polling for each line
    lineIds.forEach(lineId => {
      setTimeout(() => pollLineStatus(lineId), pollInterval);
    });
  };

  // Auto-refresh script details periodically to catch status updates
  useEffect(() => {
    if (script && !loading) {
      const interval = setInterval(() => {
        fetchScriptDetails(true); // Pass true for silent refresh
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [script, loading, fetchScriptDetails]);

  // Check stitch readiness when script details change
  useEffect(() => {
    if (scriptDetails && !loading) {
      checkStitchReadiness();
    }
  }, [scriptDetails, loading]);

  const handleStatusUpdate = () => {
    // Called when a line completes TTS or frame generation
    fetchScriptDetails(true); // Silent refresh
  };

  // Stitch-related functions
  const checkStitchReadiness = async () => {
    try {
      const status = await scriptService.checkStitchReadiness(script.script_id);
      setStitchStatus(status);
      return status;
    } catch (error) {
      console.error('Error checking stitch readiness:', error);
      setStitchStatus({ status: 'error', message: error.message });
      return null;
    }
  };

  const handleStitchVideo = async () => {
    setIsStitching(true);
    try {
      const result = await scriptService.processStitch(script.script_id);
      setStitchStatus(result);
      
      if (result.status === 'complete') {
        alert('Final video created successfully!');
        // Refresh script details to update status
        fetchScriptDetails(true);
      } else {
        alert(`Stitching status: ${result.message}`);
      }
    } catch (error) {
      console.error('Error stitching video:', error);
      alert(`Failed to stitch video: ${error.message}`);
      setStitchStatus({ status: 'error', message: error.message });
    } finally {
      setIsStitching(false);
    }
  };

  const handleDownloadFinalVideo = () => {
    const downloadUrl = scriptService.getFinalVideoUrl(script.script_id);
    window.open(downloadUrl, '_blank');
  };

  const isAllFramesComplete = () => {
    if (!scriptDetails || !scriptDetails.lines) return false;
    return scriptDetails.lines.every(line => line.avatar_status === 'complete');
  };

  const canStitchVideo = () => {
    return isAllFramesComplete() && scriptDetails?.status !== 'complete';
  };

  const isFinalVideoReady = () => {
    return scriptDetails?.status === 'complete';
  };

  const handleSyncStuckJobs = async () => {
    try {
      const response = await fetch('http://localhost:8004/avatar/sync-stuck-jobs', {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (response.ok) {
        if (result.updated > 0) {
          alert(`Successfully synced ${result.updated} stuck jobs! Refreshing status...`);
          // Refresh script details after a short delay
          setTimeout(() => fetchScriptDetails(), 2000);
        } else {
          alert('No stuck jobs found to sync.');
        }
      } else {
        alert(`Failed to sync stuck jobs: ${result.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error syncing stuck jobs:', error);
      alert(`Failed to sync stuck jobs: ${error.message}`);
    }
  };

  const hasStuckJobs = () => {
    if (!scriptDetails || !scriptDetails.lines) return false;
    return scriptDetails.lines.some(line => 
      line.avatar_status === 'processing' && 
      line.tts_status === 'complete'
    );
  };

  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="modal-content modal-large">
          <div className="loading-container">
            <Loader className="spin" size={32} />
            <p>Loading script details...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content modal-large" onClick={e => e.stopPropagation()}>
          <div className="modal-header">
            <h3>Error</h3>
            <button className="btn-icon" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
          <div className="modal-form">
            <div className="alert alert-error">
              <AlertCircle size={16} />
              {error}
            </div>
            <div className="modal-actions">
              <button onClick={onClose} className="btn-secondary">Close</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-xlarge" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{scriptDetails.title}</h3>
            <div className="script-meta-info">
              <span className="script-format">{scriptDetails.format_type}</span>
              <span className="script-length">{scriptDetails.length_minutes} minutes</span>
              <span className={`script-status status-${scriptDetails.status}`}>
                {scriptDetails.status.charAt(0).toUpperCase() + scriptDetails.status.slice(1)}
              </span>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-form">
          <div className="script-editor">
            <div className="script-toolbar">
              <div className="script-info">
                <h4>Script Lines ({scriptDetails.lines.length} lines)</h4>
                <div className="processing-summary">
                  <div className="tts-summary">
                    <span className="section-label">TTS:</span>
                    <span className="tts-stat tts-complete">{getCompletedTTSCount()} Complete</span>
                    <span className="tts-stat tts-remaining">{getRemainingTTSCount()} Remaining</span>
                  </div>
                  <div className="frame-summary">
                    <span className="section-label">Frames:</span>
                    <span className="frame-stat frame-complete">{getCompletedFrameCount()} Complete</span>
                    <span className="frame-stat frame-remaining">{getRemainingFrameCount()} Ready</span>
                  </div>
                </div>
              </div>
              <div className="script-actions">
                <button 
                  className="btn-primary"
                  onClick={handleGenerateTTS}
                  disabled={getRemainingTTSCount() === 0}
                >
                  {getRemainingTTSCount() === 0 
                    ? 'All TTS Complete' 
                    : `Generate TTS (${getRemainingTTSCount()})`}
                </button>
                <button 
                  className="btn-secondary"
                  onClick={handleGenerateFrames}
                  disabled={getRemainingFrameCount() === 0 || frameGenerationStatus.isProcessing}
                >
                  {frameGenerationStatus.isProcessing ? (
                    <>
                      <div className="spinner-small" />
                      Processing...
                    </>
                  ) : getRemainingFrameCount() === 0 
                    ? 'No Frames Ready' 
                    : `Generate Frames (${getRemainingFrameCount()})`}
                </button>
                {frameGenerationStatus.failedLines.length > 0 && (
                  <button 
                    className="btn-danger"
                    onClick={retryFailedFrameGeneration}
                    disabled={frameGenerationStatus.isProcessing}
                    title={`Retry ${frameGenerationStatus.failedLines.length} failed frame generation attempts`}
                  >
                    <RotateCcw size={16} />
                    Retry Failed ({frameGenerationStatus.failedLines.length})
                  </button>
                )}
                {hasStuckJobs() && (
                  <button 
                    className="btn-secondary"
                    onClick={handleSyncStuckJobs}
                    title="Sync stuck frame generation jobs"
                  >
                    <RotateCcw size={16} />
                    Fix Stuck Jobs
                  </button>
                )}
                {isFinalVideoReady() ? (
                  <button 
                    className="btn-success"
                    onClick={handleDownloadFinalVideo}
                    title="Download Final Video"
                  >
                    <Download size={16} />
                    Download Final Video
                  </button>
                ) : (
                  <button 
                    className="btn-accent"
                    onClick={handleStitchVideo}
                    disabled={!canStitchVideo() || isStitching}
                    title={!canStitchVideo() ? 'Complete all frames first' : 'Create final video'}
                  >
                    {isStitching ? (
                      <>
                        <div className="spinner-small" />
                        Stitching...
                      </>
                    ) : (
                      <>
                        <Video size={16} />
                        {canStitchVideo() ? 'Create Final Video' : 'Waiting for Frames'}
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            <div className="script-lines">
              {scriptDetails.lines.map((line, index) => (
                <ScriptLine
                  key={line.line_id}
                  line={line}
                  index={index}
                  isEditing={editingLine === line.line_id}
                  onEdit={() => setEditingLine(line.line_id)}
                  onSave={(newText) => handleSaveEdit(line.line_id, newText)}
                  onCancel={() => setEditingLine(null)}
                  onStatusUpdate={handleStatusUpdate}
                />
              ))}
            </div>
          </div>

          <div className="modal-actions">
            <button onClick={onClose} className="btn-secondary">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EditScriptModal; 