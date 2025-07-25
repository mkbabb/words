/**
 * Detect part of speech from definition text
 */
export function detectPartOfSpeech(definition: string): string {
  const def = definition.toLowerCase();
  
  // Verb indicators
  if (def.startsWith('to ') || 
      def.match(/^(doing|making|having|being|getting|taking|giving|going|coming|showing|telling|asking|working|looking|thinking|feeling|seeing|hearing|knowing|wanting|needing|helping|moving|playing|living|dying|learning|changing|opening|closing|starting|stopping|finding|losing|winning|building|breaking|bringing|buying|selling|sending|receiving|speaking|writing|reading|eating|drinking|sleeping|waking)/)) {
    return 'verb';
  }
  
  // Adjective indicators
  if (def.match(/^(describing|characterized by|having the quality|being|showing|expressing|full of|lacking|without)/)) {
    return 'adjective';
  }
  
  // Adverb indicators
  if (def.match(/^(in a .* manner|in a way that|with|by means of)/) ||
      def.includes('manner') && def.includes('way')) {
    return 'adverb';
  }
  
  // Person/being indicators
  if (def.match(/\b(person|people|someone|one who|individual|human|man|woman|child)\b/)) {
    return 'noun';
  }
  
  // Action/event noun indicators
  if (def.match(/\b(act of|action of|process of|state of|condition of|quality of|instance of)\b/)) {
    return 'noun';
  }
  
  // Default to noun
  return 'noun';
}