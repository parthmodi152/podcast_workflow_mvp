import React, { useState, useEffect } from 'react';
import { User, Plus, AlertCircle, Loader } from 'lucide-react';
import { voiceService } from '../services/voiceService';
import CharacterCard from './CharacterCard';
import CreateCharacterModal from './CreateCharacterModal';
import EditImageModal from './EditImageModal';

function CharacterClonesPanel() {
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedCharacter, setSelectedCharacter] = useState(null);
  
  // Fetch characters on component mount
  useEffect(() => {
    fetchCharacters();
  }, []);
  
  const fetchCharacters = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await voiceService.getVoices();
      setCharacters(data);
    } catch (err) {
      console.error('Failed to fetch characters:', err);
      setError('Failed to load characters. Please check if the voice service is running.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleEditImage = (character) => {
    setSelectedCharacter(character);
    setShowEditModal(true);
  };

  const handleDeleteCharacter = async (characterId) => {
    if (!window.confirm('Are you sure you want to delete this character? This action cannot be undone.')) {
      return;
    }
    
    try {
      await voiceService.deleteVoice(characterId);
      fetchCharacters(); // Refresh the list
    } catch (err) {
      alert(`Delete functionality: ${err.message}`);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Character Clones</h2>
        <button 
          className="btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={20} />
          Create New Character
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
          <p>Loading characters...</p>
        </div>
      ) : (
        <div className="characters-grid">
          {characters.length === 0 ? (
            <div className="empty-state">
              <User size={64} />
              <h3>No Characters Yet</h3>
              <p>Create your first character clone to get started with podcast generation.</p>
            </div>
          ) : (
            characters.map(character => (
              <CharacterCard
                key={character.id}
                character={character}
                onEditImage={() => handleEditImage(character)}
                onDelete={() => handleDeleteCharacter(character.id)}
              />
            ))
          )}
        </div>
      )}

      {/* Create Character Modal */}
      {showCreateModal && (
        <CreateCharacterModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchCharacters();
          }}
        />
      )}

      {/* Edit Image Modal */}
      {showEditModal && selectedCharacter && (
        <EditImageModal
          character={selectedCharacter}
          onClose={() => {
            setShowEditModal(false);
            setSelectedCharacter(null);
          }}
          onSuccess={() => {
            setShowEditModal(false);
            setSelectedCharacter(null);
            fetchCharacters();
          }}
        />
      )}
    </div>
  );
}

export default CharacterClonesPanel; 