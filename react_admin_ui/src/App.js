// /home/ubuntu/podcast_workflow_mvp/react_admin_ui/src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';

// Main App component
function App() {
  const [activeTab, setActiveTab] = useState('voices');
  
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Podcast Workflow Admin</h1>
        <nav className="app-nav">
          <button 
            className={activeTab === 'voices' ? 'active' : ''} 
            onClick={() => setActiveTab('voices')}
          >
            Voices
          </button>
          <button 
            className={activeTab === 'scripts' ? 'active' : ''} 
            onClick={() => setActiveTab('scripts')}
          >
            Scripts
          </button>
          <button 
            className={activeTab === 'episodes' ? 'active' : ''} 
            onClick={() => setActiveTab('episodes')}
          >
            Episodes
          </button>
        </nav>
      </header>
      
      <main className="app-content">
        {activeTab === 'voices' && <VoicesPanel />}
        {activeTab === 'scripts' && <ScriptsPanel />}
        {activeTab === 'episodes' && <EpisodesPanel />}
      </main>
      
      <footer className="app-footer">
        <p>Podcast Workflow MVP - Local Testing Environment</p>
      </footer>
    </div>
  );
}

// Voices Panel Component
function VoicesPanel() {
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  
  // Fetch voices on component mount
  useEffect(() => {
    fetchVoices();
  }, []);
  
  const fetchVoices = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8001/voices');
      if (!response.ok) {
        throw new Error(`Error fetching voices: ${response.statusText}`);
      }
      
      const data = await response.json();
      setVoices(data);
    } catch (err) {
      console.error('Failed to fetch voices:', err);
      setError('Failed to load voices. Please check if the voice service is running.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleVoiceUpload = async (event) => {
    event.preventDefault();
    setUploadStatus({ status: 'uploading', message: 'Uploading voice...' });
    
    const formData = new FormData(event.target);
    
    try {
      const response = await fetch('http://localhost:8001/voices', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error uploading voice: ${errorText}`);
      }
      
      const result = await response.json();
      setUploadStatus({ 
        status: 'success', 
        message: `Voice uploaded successfully! Voice ID: ${result.voice_id}` 
      });
      
      // Refresh the voices list
      fetchVoices();
      
      // Reset the form
      event.target.reset();
    } catch (err) {
      console.error('Failed to upload voice:', err);
      setUploadStatus({ 
        status: 'error', 
        message: `Failed to upload voice: ${err.message}` 
      });
    }
  };
  
  return (
    <div className="panel">
      <h2>Voice Management</h2>
      
      <div className="card">
        <h3>Upload New Voice</h3>
        <form onSubmit={handleVoiceUpload}>
          <div className="form-group">
            <label htmlFor="name">Voice Name:</label>
            <input 
              type="text" 
              id="name" 
              name="name" 
              required 
              placeholder="e.g., Host Voice"
            />
          </div>

          <div className="form-group">
            <label htmlFor="speaker_image">Speaker Image (Optional, for Avatar):</label>
            <input 
              type="file" 
              id="speaker_image" 
              name="speaker_image" 
              accept="image/jpeg,image/png,image/webp"
            />
            <small>Upload a clear portrait image (JPEG, PNG, WebP) for the speaker.</small>
          </div>
          
          <div className="form-group">
            <label htmlFor="files">Audio Files (MP3 or WAV):</label>
            <input 
              type="file" 
              id="files" 
              name="files" 
              required 
              multiple 
              accept=".mp3,.wav"
            />
            <small>Upload 1-2 minutes of clean, single-speaker audio for best results.</small>
          </div>
          
          <button type="submit" className="btn-primary">Upload Voice</button>
        </form>
        
        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.status}`}>
            {uploadStatus.message}
          </div>
        )}
      </div>
      
      <div className="card">
        <h3>Voice Catalogue</h3>
        {loading && <p>Loading voices...</p>}
        {error && <p className="error">{error}</p>}
        
        {!loading && !error && voices.length === 0 && (
          <p>No voices found. Upload a voice to get started.</p>
        )}
        
        {!loading && !error && voices.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Voice ID</th>
                <th>Name</th>
              </tr>
            </thead>
            <tbody>
              {voices.map(voice => (
                <tr key={voice.id}>
                  <td>{voice.id}</td>
                  <td>{voice.voice_id}</td>
                  <td>{voice.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        
        <button onClick={fetchVoices} className="btn-secondary">
          Refresh List
        </button>
      </div>
    </div>
  );
}

// Scripts Panel Component
function ScriptsPanel() {
  const [voices, setVoices] = useState([]);
  const [scripts, setScripts] = useState([]);
  const [selectedScript, setSelectedScript] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [createStatus, setCreateStatus] = useState(null);
  
  // Fetch voices and scripts on component mount
  useEffect(() => {
    fetchVoices();
    fetchScripts();
  }, []);
  
  const fetchVoices = async () => {
    try {
      const response = await fetch('http://localhost:8001/voices');
      if (!response.ok) {
        throw new Error(`Error fetching voices: ${response.statusText}`);
      }
      
      const data = await response.json();
      setVoices(data);
    } catch (err) {
      console.error('Failed to fetch voices:', err);
      setError('Failed to load voices. Please check if the voice service is running.');
    }
  };
  
  const fetchScripts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8002/scripts');
      if (!response.ok) {
        throw new Error(`Error fetching scripts: ${response.statusText}`);
      }
      
      const data = await response.json();
      setScripts(data);
    } catch (err) {
      console.error('Failed to fetch scripts:', err);
      setError('Failed to load scripts. Please check if the script service is running.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleScriptCreate = async (event) => {
    event.preventDefault();
    setCreateStatus({ status: 'creating', message: 'Creating script...' });
    
    const formData = new FormData(event.target);
    const title = formData.get('title');
    const lengthMinutes = parseInt(formData.get('length_minutes'), 10);
    
    // Get selected speakers
    const speakerRows = document.querySelectorAll('.speaker-row');
    const speakers = Array.from(speakerRows).map(row => {
      const role = row.querySelector('[name="role"]').value;
      const voiceId = row.querySelector('[name="voice_id"]').value;
      return { role, voice_id: voiceId };
    });
    
    const scriptData = {
      title,
      length_minutes: lengthMinutes,
      speakers
    };
    
    try {
      const response = await fetch('http://localhost:8002/scripts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scriptData),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error creating script: ${errorText}`);
      }
      
      const result = await response.json();
      setCreateStatus({ 
        status: 'success', 
        message: `Script created successfully! Script ID: ${result.script_id}` 
      });
      
      // Refresh the scripts list
      fetchScripts();
      
      // Reset the form
      event.target.reset();
      document.getElementById('speakers-container').innerHTML = '';
    } catch (err) {
      console.error('Failed to create script:', err);
      setCreateStatus({ 
        status: 'error', 
        message: `Failed to create script: ${err.message}` 
      });
    }
  };
  
  const addSpeakerRow = () => {
    const speakersContainer = document.getElementById('speakers-container');
    const newRow = document.createElement('div');
    newRow.className = 'speaker-row';
    
    newRow.innerHTML = `
      <div class="form-group">
        <label>Role:</label>
        <input type="text" name="role" required placeholder="e.g., Host, Guest">
      </div>
      <div class="form-group">
        <label>Voice:</label>
        <select name="voice_id" required>
          <option value="">Select a voice</option>
          ${voices.map(voice => `<option value="${voice.voice_id}">${voice.name}</option>`).join('')}
        </select>
      </div>
      <button type="button" class="btn-remove" onclick="this.parentNode.remove()">Remove</button>
    `;
    
    speakersContainer.appendChild(newRow);
  };
  
  const viewScriptDetails = async (scriptId) => {
    try {
      const response = await fetch(`http://localhost:8002/scripts/${scriptId}`);
      if (!response.ok) {
        throw new Error(`Error fetching script details: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSelectedScript(data);
    } catch (err) {
      console.error('Failed to fetch script details:', err);
      setError(`Failed to load script details: ${err.message}`);
    }
  };
  
  return (
    <div className="panel">
      <h2>Script Management</h2>
      
      <div className="card">
        <h3>Create New Script</h3>
        <form onSubmit={handleScriptCreate}>
          <div className="form-group">
            <label htmlFor="title">Script Title:</label>
            <input 
              type="text" 
              id="title" 
              name="title" 
              required 
              placeholder="e.g., Why LLMs Matter"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="length_minutes">Length (minutes):</label>
            <input 
              type="number" 
              id="length_minutes" 
              name="length_minutes" 
              required 
              min="1" 
              max="60" 
              defaultValue="5"
            />
          </div>
          
          <h4>Speakers</h4>
          <div id="speakers-container"></div>
          
          <button type="button" onClick={addSpeakerRow} className="btn-secondary">
            Add Speaker
          </button>
          
          <button type="submit" className="btn-primary">Create Script</button>
        </form>
        
        {createStatus && (
          <div className={`create-status ${createStatus.status}`}>
            {createStatus.message}
          </div>
        )}
      </div>
      
      <div className="card">
        <h3>Scripts List</h3>
        {loading && <p>Loading scripts...</p>}
        {error && <p className="error">{error}</p>}
        
        {!loading && !error && scripts.length === 0 && (
          <p>No scripts found. Create a script to get started.</p>
        )}
        
        {!loading && !error && scripts.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {scripts.map(script => (
                <tr key={script.script_id}>
                  <td>{script.script_id}</td>
                  <td>{script.title}</td>
                  <td>{script.status}</td>
                  <td>
                    <button 
                      onClick={() => viewScriptDetails(script.script_id)}
                      className="btn-small"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        
        <button onClick={fetchScripts} className="btn-secondary">
          Refresh List
        </button>
      </div>
      
      {selectedScript && (
        <div className="card">
          <h3>Script Details: {selectedScript.title}</h3>
          <p><strong>Status:</strong> {selectedScript.status}</p>
          <p><strong>Length:</strong> {selectedScript.length_minutes} minutes</p>
          
          <h4>Lines</h4>
          <table className="data-table">
            <thead>
              <tr>
                <th>Line ID</th>
                <th>Speaker</th>
                <th>Text</th>
                <th>TTS Status</th>
              </tr>
            </thead>
            <tbody>
              {selectedScript.lines.map(line => (
                <tr key={line.line_id}>
                  <td>{line.line_id}</td>
                  <td>{line.speaker}</td>
                  <td>{line.text}</td>
                  <td>{line.tts_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          
          <button onClick={() => setSelectedScript(null)} className="btn-secondary">
            Close Details
          </button>
        </div>
      )}
    </div>
  );
}

// Episodes Panel Component
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
      const response = await fetch('http://localhost:8002/scripts?status=complete');
      if (!response.ok) {
        throw new Error(`Error fetching episodes: ${response.statusText}`);
      }
      
      const data = await response.json();
      setEpisodes(data);
    } catch (err) {
      console.error('Failed to fetch episodes:', err);
      setError('Failed to load episodes. Please check if the script service is running.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="panel">
      <h2>Completed Episodes</h2>
      
      <div className="card">
        <h3>Episodes List</h3>
        {loading && <p>Loading episodes...</p>}
        {error && <p className="error">{error}</p>}
        
        {!loading && !error && episodes.length === 0 && (
          <p>No completed episodes found. Episodes will appear here when processing is complete.</p>
        )}
        
        {!loading && !error && episodes.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Length</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {episodes.map(episode => (
                <tr key={episode.script_id}>
                  <td>{episode.script_id}</td>
                  <td>{episode.title}</td>
                  <td>{episode.length_minutes} minutes</td>
                  <td>
                    <a 
                      href={`/data/podcast-final/${episode.script_id}_final_episode.mp4`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn-small"
                    >
                      View Episode
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        
        <button onClick={fetchEpisodes} className="btn-secondary">
          Refresh List
        </button>
      </div>
    </div>
  );
}

export default App;
