import React from 'react';
import { Edit3, Trash2 } from 'lucide-react';
import { getImageUrl, handleImageError } from '../utils/imageUtils';

function CharacterCard({ character, onEditImage, onDelete }) {
  return (
    <div className="character-card">
      <div className="character-image">
        <img 
          src={getImageUrl(character.image_path)}
          alt={character.name}
          onError={handleImageError}
        />
      </div>
      
      <div className="character-info">
        <h3>{character.name}</h3>
        <p className="character-id">ID: {character.voice_id.substring(0, 8)}...</p>
      </div>
      
      <div className="character-actions">
        <button 
          className="btn-icon btn-edit"
          onClick={onEditImage}
          title="Edit Image"
        >
          <Edit3 size={16} />
        </button>
        <button 
          className="btn-icon btn-delete"
          onClick={onDelete}
          title="Delete Character"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}

export default CharacterCard; 