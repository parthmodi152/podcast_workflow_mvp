// /home/ubuntu/podcast_workflow_mvp/react_admin_ui/src/App.js
import React, { useState } from 'react';
import CharacterClonesPanel from './components/CharacterClonesPanel';
import ScriptsPanel from './components/ScriptsPanel';
import EpisodesPanel from './components/EpisodesPanel';
import './App.css';

// Main App component
function App() {
  const [activeTab, setActiveTab] = useState('characters');
  
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Podcast Workflow Admin</h1>
        <nav className="app-nav">
          <button 
            className={activeTab === 'characters' ? 'active' : ''} 
            onClick={() => setActiveTab('characters')}
          >
            Character Clones
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
        {activeTab === 'characters' && <CharacterClonesPanel />}
        {activeTab === 'scripts' && <ScriptsPanel />}
        {activeTab === 'episodes' && <EpisodesPanel />}
      </main>
      
      <footer className="app-footer">
        <p>Podcast Workflow MVP - Local Testing Environment</p>
      </footer>
    </div>
  );
}

export default App;
