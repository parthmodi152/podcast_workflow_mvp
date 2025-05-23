import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, X, Check, AlertCircle, Loader } from 'lucide-react';
import { scriptService } from '../services/scriptService';
import { formatTypeLabels, getFormatDescription, getGuestLimits } from '../utils/formatUtils';

function CreateScriptModal({ characters, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    title: '',
    format_type: 'interview',
    length_minutes: 5,
    speakers: [
      { role: 'host', name: '', voice_id: '' },
      { role: 'guest', name: '', voice_id: '' }
    ],
    survey_responses: '',
    article_url: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Update speakers when format changes - use callback to avoid circular dependency
  const updateSpeakersForFormat = useCallback(() => {
    setFormData(prev => {
      const newSpeakers = [...prev.speakers];
      
      // Ensure we always have exactly one host
      const hostIndex = newSpeakers.findIndex(s => s.role === 'host');
      if (hostIndex === -1) {
        newSpeakers.unshift({ role: 'host', name: '', voice_id: '' });
      }
      
      // Filter out extra hosts (keep only the first one)
      const filteredSpeakers = newSpeakers.filter((speaker, index) => {
        if (speaker.role === 'host') {
          return index === newSpeakers.findIndex(s => s.role === 'host');
        }
        return true;
      });
      
      // Ensure minimum guests based on format
      const guestCount = filteredSpeakers.filter(s => s.role === 'guest').length;
      const minGuests = 1; // All formats need at least 1 guest
      const maxGuests = prev.format_type === 'interview' ? 1 : 10; // Interview: 1 guest, others: multiple
      
      // Add guests if we don't have enough
      if (guestCount < minGuests) {
        const guestsToAdd = minGuests - guestCount;
        for (let i = 0; i < guestsToAdd; i++) {
          filteredSpeakers.push({ role: 'guest', name: '', voice_id: '' });
        }
      }
      
      // Remove excess guests for interview format
      if (prev.format_type === 'interview' && guestCount > maxGuests) {
        const updatedSpeakers = [];
        let guestsAdded = 0;
        
        for (const speaker of filteredSpeakers) {
          if (speaker.role === 'host') {
            updatedSpeakers.push(speaker);
          } else if (speaker.role === 'guest' && guestsAdded < maxGuests) {
            updatedSpeakers.push(speaker);
            guestsAdded++;
          }
        }
        
        return { ...prev, speakers: updatedSpeakers };
      }
      
      return { ...prev, speakers: filteredSpeakers };
    });
  }, []);

  useEffect(() => {
    updateSpeakersForFormat();
  }, [formData.format_type, updateSpeakersForFormat]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!formData.title.trim()) {
      setError('Script title is required');
      return;
    }

    // Check host validation
    const hosts = formData.speakers.filter(s => s.role === 'host');
    if (hosts.length !== 1) {
      setError('Exactly one host is required');
      return;
    }

    // Check guest validation
    const guests = formData.speakers.filter(s => s.role === 'guest');
    if (guests.length < 1) {
      setError('At least one guest is required');
      return;
    }

    if (formData.format_type === 'interview' && guests.length > 1) {
      setError('Interview format allows only one guest');
      return;
    }

    // Check if all speakers have name and voice
    if (formData.speakers.some(s => !s.name.trim() || !s.voice_id)) {
      setError('All speakers must have a name and selected character');
      return;
    }

    // Check survey responses
    if (!formData.survey_responses.trim()) {
      setError('Survey responses are required to generate relevant content');
      return;
    }

    if (formData.format_type === 'article' && !formData.article_url.trim()) {
      setError('Article URL is required for article discussion format');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const scriptData = {
        title: formData.title,
        format_type: formData.format_type,
        length_minutes: formData.length_minutes,
        speakers: formData.speakers,
        questionnaire_answers: [
          {
            question: "Guest Survey Responses and Content Guidelines",
            answer: formData.survey_responses
          }
        ],
        ...(formData.format_type === 'article' && { article_url: formData.article_url })
      };

      const result = await scriptService.createScript(scriptData);
      console.log('Script created successfully:', result);
      onSuccess();
      
    } catch (err) {
      console.error('Failed to create script:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const updateSpeaker = (index, field, value) => {
    const newSpeakers = [...formData.speakers];
    
    // Prevent changing host role or having multiple hosts
    if (field === 'role') {
      if (value === 'host') {
        const hostExists = newSpeakers.some((s, i) => s.role === 'host' && i !== index);
        if (hostExists) {
          setError('Only one host is allowed');
          return;
        }
      }
    }
    
    newSpeakers[index][field] = value;
    setFormData(prev => ({ ...prev, speakers: newSpeakers }));
  };

  const addSpeaker = () => {
    // Check if we can add more guests based on format
    const currentGuests = formData.speakers.filter(s => s.role === 'guest').length;
    const maxGuests = formData.format_type === 'interview' ? 1 : 10;
    
    if (currentGuests >= maxGuests) {
      if (formData.format_type === 'interview') {
        setError('Interview format allows only one guest');
      } else {
        setError('Maximum number of guests reached');
      }
      return;
    }

    setFormData(prev => ({
      ...prev,
      speakers: [...prev.speakers, { role: 'guest', name: '', voice_id: '' }]
    }));
  };

  const removeSpeaker = (index) => {
    const speaker = formData.speakers[index];
    
    // Prevent removing the host
    if (speaker.role === 'host') {
      setError('Host cannot be removed');
      return;
    }
    
    // Prevent removing if we'd have less than 1 guest
    const currentGuests = formData.speakers.filter(s => s.role === 'guest').length;
    if (currentGuests <= 1) {
      setError('At least one guest is required');
      return;
    }

    const newSpeakers = formData.speakers.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, speakers: newSpeakers }));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Podcast Script</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && (
            <div className="alert alert-error">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* Basic Information */}
          <div className="form-section">
            <h4>Basic Information</h4>
            
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="title">Script Title *</label>
                <input
                  id="title"
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., The Future of AI in Healthcare"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="length_minutes">Length (minutes) *</label>
                <input
                  id="length_minutes"
                  type="number"
                  min="1"
                  max="60"
                  value={formData.length_minutes}
                  onChange={(e) => setFormData(prev => ({ ...prev, length_minutes: parseInt(e.target.value) }))}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="format_type">Podcast Format *</label>
              <select
                id="format_type"
                value={formData.format_type}
                onChange={(e) => setFormData(prev => ({ ...prev, format_type: e.target.value }))}
                required
              >
                {Object.entries(formatTypeLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <small>{getFormatDescription(formData.format_type)}</small>
            </div>

            {formData.format_type === 'article' && (
              <div className="form-group">
                <label htmlFor="article_url">Article URL *</label>
                <input
                  id="article_url"
                  type="url"
                  value={formData.article_url}
                  onChange={(e) => setFormData(prev => ({ ...prev, article_url: e.target.value }))}
                  placeholder="https://example.com/article"
                  required
                />
                <small>URL of the article or blog post to discuss</small>
              </div>
            )}
          </div>

          {/* Speakers */}
          <div className="form-section">
            <h4>Speakers & Characters ({getGuestLimits(formData.speakers, formData.format_type)})</h4>
            
            {formData.speakers.map((speaker, index) => (
              <div key={index} className="speaker-config">
                <div className="speaker-config-header">
                  <h5>{speaker.role.charAt(0).toUpperCase() + speaker.role.slice(1)}</h5>
                  {speaker.role === 'guest' && formData.speakers.filter(s => s.role === 'guest').length > 1 && (
                    <button
                      type="button"
                      className="btn-icon btn-delete"
                      onClick={() => removeSpeaker(index)}
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Role</label>
                    <select
                      value={speaker.role}
                      onChange={(e) => updateSpeaker(index, 'role', e.target.value)}
                      disabled={speaker.role === 'host'} // Host role cannot be changed
                      required
                    >
                      <option value="host">Host</option>
                      <option value="guest">Guest</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Speaker Name</label>
                    <input
                      type="text"
                      value={speaker.name}
                      onChange={(e) => updateSpeaker(index, 'name', e.target.value)}
                      placeholder="e.g., Dr. Sarah Johnson"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>Character Voice</label>
                    <select
                      value={speaker.voice_id}
                      onChange={(e) => updateSpeaker(index, 'voice_id', e.target.value)}
                      required
                    >
                      <option value="">Select a character...</option>
                      {characters.map(character => (
                        <option key={character.voice_id} value={character.voice_id}>
                          {character.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            ))}

            {(formData.format_type !== 'interview' || 
              formData.speakers.filter(s => s.role === 'guest').length < 1) && (
              <button
                type="button"
                className="btn-secondary"
                onClick={addSpeaker}
              >
                <Plus size={16} />
                Add Another Guest
              </button>
            )}
          </div>

          {/* Survey Responses */}
          <div className="form-section">
            <h4>Guest Survey Responses</h4>
            <p>Paste the survey responses from your guests. This should include their answers to questions about the topic, their expertise, talking points, and any specific content they want to cover.</p>
            
            <div className="form-group">
              <label htmlFor="survey_responses">Survey Responses *</label>
              <textarea
                id="survey_responses"
                value={formData.survey_responses}
                onChange={(e) => setFormData(prev => ({ ...prev, survey_responses: e.target.value }))}
                placeholder="Paste the complete survey responses from your guests here. Include questions and answers, talking points, areas of expertise, and any specific content they want to discuss..."
                rows="8"
                required
              />
              <small>Include all relevant information from guest surveys to generate targeted content</small>
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary" 
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader className="spin" size={16} />
                  Generating Script...
                </>
              ) : (
                <>
                  <Check size={16} />
                  Generate Script
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateScriptModal; 