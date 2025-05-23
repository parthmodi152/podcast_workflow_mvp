import React, { useState, useEffect } from 'react';
import { User, Plus, AlertCircle, Loader } from 'lucide-react';
import { voiceService } from '../services/voiceService';
import { scriptService } from '../services/scriptService';
import ScriptCard from './ScriptCard';
import CreateScriptModal from './CreateScriptModal';
import EditScriptModal from './EditScriptModal';

function ScriptsPanel() {
  const [characters, setCharacters] = useState([]);
  const [scripts, setScripts] = useState([]);
  const [selectedScript, setSelectedScript] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  
  // Fetch characters and scripts on component mount
  useEffect(() => {
    fetchCharacters();
    fetchScripts();
  }, []);
  
  const fetchCharacters = async () => {
    try {
      const data = await voiceService.getVoices();
      setCharacters(data);
    } catch (err) {
      console.error('Failed to fetch characters:', err);
      setError('Failed to load characters. Please check if the voice service is running.');
    }
  };
  
  const fetchScripts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await scriptService.getScripts();
      setScripts(data);
    } catch (err) {
      console.error('Failed to fetch scripts:', err);
      setError('Failed to load scripts. Please check if the script service is running.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleViewScript = (script) => {
    setSelectedScript(script);
    setShowEditModal(true);
  };

  const handleGenerateTTS = async (scriptId) => {
    try {
      await scriptService.generateTTS(scriptId);
      // Refresh scripts to update status
      fetchScripts();
      alert('TTS generation started successfully!');
    } catch (err) {
      console.error('Failed to generate TTS:', err);
      alert(`Failed to generate TTS: ${err.message}`);
    }
  };

  const handleDeleteScript = async (scriptId) => {
    if (!window.confirm('Are you sure you want to delete this script? This action cannot be undone.')) {
      return;
    }

    try {
      await scriptService.deleteScript(scriptId);
      // Refresh scripts list after successful deletion
      fetchScripts();
      alert('Script deleted successfully!');
    } catch (err) {
      console.error('Failed to delete script:', err);
      alert(`Failed to delete script: ${err.message}`);
    }
  };
  
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Script Generation</h2>
        <button 
          className="btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={20} />
          Create New Script
        </button>
      </div>
      
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}
      
      {loading ? (
        <div className="loading-container">
          <Loader className="spin" size={32} />
          <p>Loading scripts...</p>
        </div>
      ) : (
        <div className="scripts-grid">
          {scripts.length === 0 ? (
            <div className="empty-state">
              <User size={64} />
              <h3>No Scripts Yet</h3>
              <p>Create your first podcast script to get started with content generation.</p>
            </div>
          ) : (
            scripts.map(script => (
              <ScriptCard
                key={script.script_id}
                script={script}
                onView={() => handleViewScript(script)}
                onGenerateTTS={() => handleGenerateTTS(script.script_id)}
                onDelete={handleDeleteScript}
              />
            ))
          )}
        </div>
      )}

      {/* Create Script Modal */}
      {showCreateModal && (
        <CreateScriptModal
          characters={characters}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchScripts();
          }}
        />
      )}

      {/* Edit Script Modal */}
      {showEditModal && selectedScript && (
        <EditScriptModal
          script={selectedScript}
          onClose={() => {
            setShowEditModal(false);
            setSelectedScript(null);
          }}
          onSuccess={() => {
            setShowEditModal(false);
            setSelectedScript(null);
            fetchScripts();
          }}
        />
      )}
    </div>
  );
}

export default ScriptsPanel; 