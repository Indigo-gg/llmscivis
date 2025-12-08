/**
 * Score utility functions for converting between 0-1 and 0-100 scales
 */

/**
 * Convert score from 0-1 scale to 0-100 scale
 * @param {number|string} score - Score in 0-1 scale
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {number|null} Score in 0-100 scale or null if invalid
 */
export function convertToHundredScale(score, decimals = 1) {
  if (score === null || score === undefined || score === '') {
    return null;
  }
  
  const numScore = typeof score === 'string' ? parseFloat(score) : score;
  
  if (isNaN(numScore)) {
    return null;
  }
  
  // Convert to 100 scale and round
  const hundredScale = numScore * 100;
  return Number(hundredScale.toFixed(decimals));
}

/**
 * Format score for display (0-100 scale without % sign)
 * @param {number|string} score - Score in 0-1 scale
 * @param {boolean} showUnit - Whether to show unit (default: false)
 * @returns {string} Formatted score string
 */
export function formatScore(score, showUnit = false) {
  const convertedScore = convertToHundredScale(score);
  
  if (convertedScore === null) {
    return '--';
  }
  
  return showUnit ? `${convertedScore}分` : `${convertedScore}`;
}

/**
 * Get score color based on value (0-100 scale)
 * @param {number|string} score - Score in 0-1 or 0-100 scale
 * @param {boolean} isHundredScale - Whether score is already in 100 scale
 * @returns {string} Color code
 */
export function getScoreColor(score, isHundredScale = false) {
  let numScore = typeof score === 'string' ? parseFloat(score) : score;
  
  if (isNaN(numScore) || numScore === null || numScore === 0) {
    return '#9e9e9e'; // Grey for invalid or unscored
  }
  
  // Convert to 100 scale if needed
  if (!isHundredScale && numScore <= 1) {
    numScore = numScore * 100;
  }
  
  if (numScore >= 80) return '#455a64'; // Stable blue-grey - Excellent
  if (numScore >= 60) return '#546e7a'; // Stable blue-grey - Good
  return '#607d8b'; // Stable blue-grey - Needs improvement
}

/**
 * Get score level text based on value (0-100 scale)
 * @param {number|string} score - Score in 0-1 or 0-100 scale
 * @param {boolean} isHundredScale - Whether score is already in 100 scale
 * @returns {string} Level text
 */
export function getScoreLevel(score, isHundredScale = false) {
  let numScore = typeof score === 'string' ? parseFloat(score) : score;
  
  if (isNaN(numScore) || numScore === null) {
    return 'Unknown';
  }
  
  // Convert to 100 scale if needed
  if (!isHundredScale && numScore <= 1) {
    numScore = numScore * 100;
  }
  
  if (numScore >= 90) return 'Excellent';
  if (numScore >= 80) return 'Good';
  if (numScore >= 60) return 'Pass';
  return 'Fail';
}

/**
 * Parse evaluation text from LLM response
 * Extracts structured data from XML-formatted evaluation
 * @param {string} evaluationText - Raw evaluation text from LLM
 * @returns {Object|null} Parsed evaluation object with dimensions, overall score, and critique
 */
export function parseEvaluation(evaluationText) {
  if (!evaluationText || typeof evaluationText !== 'string') {
    return null;
  }
  
  try {
    // Create a DOMParser to parse XML
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(evaluationText, 'text/xml');
    
    // Check for parsing errors
    const parserError = xmlDoc.querySelector('parsererror');
    if (parserError) {
      console.warn('XML parsing failed, returning null');
      return null;
    }
    
    // Extract dimensions
    const dimensions = {};
    const dimensionElements = xmlDoc.querySelectorAll('Dimension');
    let scores = [];
    
    dimensionElements.forEach(dimElement => {
      const name = dimElement.getAttribute('name');
      const scoreElement = dimElement.querySelector('Score');
      const reasonElement = dimElement.querySelector('Reason');
      
      if (name && scoreElement) {
        const scoreText = scoreElement.textContent.trim();
        const score = parseFloat(scoreText);
        
        if (!isNaN(score)) {
          dimensions[name] = {
            score: score,
            reason: reasonElement ? reasonElement.textContent.trim() : ''
          };
          scores.push(score);
        }
      }
    });
    
    // Extract overall score
    let overallScore = null;
    const overallElement = xmlDoc.querySelector('OverallScore');
    if (overallElement) {
      const overallText = overallElement.textContent.trim();
      overallScore = parseFloat(overallText);
    }
    
    // If no explicit overall score, calculate average from dimensions
    if ((overallScore === null || isNaN(overallScore)) && scores.length > 0) {
      overallScore = scores.reduce((sum, s) => sum + s, 0) / scores.length;
    }
    
    // Extract critique
    let critique = '';
    const critiqueElement = xmlDoc.querySelector('Critique');
    if (critiqueElement) {
      critique = critiqueElement.textContent.trim();
    }
    
    return {
      dimensions: dimensions,
      overall: overallScore,
      critique: critique
    };
  } catch (error) {
    console.error('Error parsing evaluation:', error);
    return null;
  }
}

/**
 * Convert parsed evaluation dimensions to 100 scale
 * @param {Object} parsedEvaluation - Parsed evaluation object
 * @returns {Object|null} Converted evaluation object or null
 */
export function convertEvaluationToHundredScale(parsedEvaluation) {
  if (!parsedEvaluation) {
    return null;
  }
  
  const converted = {
    overall: convertToHundredScale(parsedEvaluation.overall),
    critique: parsedEvaluation.critique || '',
    dimensions: {}
  };
  
  if (parsedEvaluation.dimensions) {
    for (const [key, value] of Object.entries(parsedEvaluation.dimensions)) {
      converted.dimensions[key] = {
        score: convertToHundredScale(value.score),
        reason: value.reason || ''
      };
    }
  }
  
  return converted;
}
