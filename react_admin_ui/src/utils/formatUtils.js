// Format type labels for podcast formats
export const formatTypeLabels = {
  interview: 'Two-Person Interview',
  roundtable: 'Round-Table Discussion',
  article: 'Article Discussion'
};

// Get format description
export const getFormatDescription = (formatType) => {
  switch (formatType) {
    case 'interview':
      return 'One-on-one conversation between host and one guest';
    case 'roundtable':
      return 'Group discussion with host and multiple guests';
    case 'article':
      return 'Discussion about a specific article or blog post';
    default:
      return '';
  }
};

// Get guest limits display
export const getGuestLimits = (speakers, formatType) => {
  const guestCount = speakers.filter(s => s.role === 'guest').length;
  if (formatType === 'interview') {
    return `${guestCount}/1 guest`;
  } else {
    return `${guestCount} guests`;
  }
};

// Get status color for script status
export const getStatusColor = (status) => {
  switch (status) {
    case 'complete': return '#2e7d32';
    case 'processing': return '#f57c00';
    case 'tts_processing': return '#1976d2';
    case 'failed': return '#d32f2f';
    default: return '#7f8c8d';
  }
};

// Get speaker color for script lines
export const getSpeakerColor = (role) => {
  switch (role) {
    case 'host': return '#1976d2';
    case 'guest': return '#388e3c';
    default: return '#7f8c8d';
  }
}; 