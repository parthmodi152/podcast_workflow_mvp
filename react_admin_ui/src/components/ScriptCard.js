import React from 'react';
import { Edit3, Check, AlertCircle, Loader, Trash2 } from 'lucide-react';
import { getStatusColor } from '../utils/formatUtils';

function ScriptCard({ script, onView, onGenerateTTS, onDelete }) {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'complete': return <Check size={16} />;
      case 'processing': return <Loader className="spin" size={16} />;
      case 'tts_processing': return <Loader className="spin" size={16} />;
      case 'failed': return <AlertCircle size={16} />;
      default: return <AlertCircle size={16} />;
    }
  };

  return (
    <div className="script-card">
      <div className="script-header">
        <h3>{script.title}</h3>
        <div className="script-status" style={{ color: getStatusColor(script.status) }}>
          {getStatusIcon(script.status)}
          <span>{script.status.charAt(0).toUpperCase() + script.status.slice(1)}</span>
        </div>
      </div>
      
      <div className="script-meta">
        <span className="script-type">{script.format_type || 'interview'}</span>
        <span className="script-length">{script.length_minutes || 5} min</span>
      </div>
      
      <div className="script-actions">
        <button 
          className="btn-secondary"
          onClick={onView}
        >
          <Edit3 size={16} />
          View & Edit
        </button>
        {script.status === 'processing' && (
          <button 
            className="btn-primary"
            onClick={onGenerateTTS}
          >
            Generate TTS
          </button>
        )}
        <button 
          className="btn-danger"
          onClick={() => onDelete(script.script_id)}
          title="Delete Script"
        >
          <Trash2 size={16} />
          Delete
        </button>
      </div>
    </div>
  );
}

export default ScriptCard; 