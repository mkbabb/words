/**
 * Simple text-to-SVG path generator for handwriting animation
 * Generates basic cursive-style paths for letters
 */

interface LetterPath {
  path: string
  width: number
  height: number
}

// Sophisticated cursive letter paths with mature, flowing strokes
const letterPaths: Record<string, LetterPath> = {
  'a': { path: 'M12,45 C16,25 28,20 42,28 C52,34 58,42 52,52 C48,58 42,62 38,60 C34,58 32,54 34,50 C36,46 40,44 44,46 L45,58', width: 65, height: 80 },
  'b': { path: 'M12,8 L12,62 C12,58 16,54 22,52 C28,50 34,50 38,54 C42,58 42,64 38,68 C34,72 28,72 22,68 C18,64 16,58 18,54', width: 50, height: 80 },
  'c': { path: 'M45,35 C35,25 25,28 20,35 C15,42 15,50 20,57 C25,64 35,67 45,57', width: 55, height: 80 },
  'd': { path: 'M48,8 L48,58 C44,42 36,35 28,38 C20,41 16,49 20,57 C24,65 32,68 40,65 C44,63 46,59 48,55', width: 58, height: 80 },
  'e': { path: 'M18,48 C28,44 38,44 42,48 C46,52 44,58 38,62 C32,66 24,66 18,62 C14,58 14,52 18,48 Z M20,50 L38,50', width: 52, height: 80 },
  'f': { path: 'M32,8 C28,6 24,8 22,12 C20,16 20,20 22,24 L22,62 M16,32 C20,30 28,30 32,32', width: 48, height: 80 },
  'g': { path: 'M42,35 C32,28 22,32 20,42 C18,52 24,58 34,58 C40,58 44,54 44,48 L44,72 C44,82 38,88 28,86 C24,85 22,82 24,80', width: 54, height: 100 },
  'h': { path: 'M12,8 L12,62 C16,45 24,38 32,42 C38,45 40,50 40,56 L40,62', width: 52, height: 80 },
  'i': { path: 'M22,32 L22,58 C22,62 24,64 26,62 M22,18 C20,16 22,14 24,16 C26,18 24,20 22,18', width: 36, height: 80 },
  'j': { path: 'M25,30 L25,70 Q20,85 10,80 M25,20 Q27,18 25,16 Q23,18 25,20', width: 35, height: 100 },
  'k': { path: 'M10,10 L10,70 M35,35 L10,45 L40,65', width: 50, height: 80 },
  'l': { path: 'M25,10 L25,60 Q30,70 35,60', width: 45, height: 80 },
  'm': { path: 'M10,30 L10,70 M10,40 Q25,20 35,30 L35,70 M35,40 Q50,20 60,30 L60,70', width: 70, height: 80 },
  'n': { path: 'M10,30 L10,70 M10,40 Q30,20 50,30 L50,70', width: 60, height: 80 },
  'o': { path: 'M30,20 Q10,25 10,45 Q10,65 30,70 Q50,65 50,45 Q50,25 30,20 Z', width: 60, height: 80 },
  'p': { path: 'M10,30 L10,85 M10,40 Q30,20 50,30 Q60,40 50,50 Q30,55 10,50', width: 60, height: 100 },
  'q': { path: 'M50,30 Q30,20 20,40 Q15,60 35,65 Q50,60 55,40 L55,85', width: 65, height: 100 },
  'r': { path: 'M10,30 L10,70 M10,40 Q25,25 35,35', width: 45, height: 80 },
  's': { path: 'M45,25 Q25,15 15,30 Q25,40 35,35 Q45,30 40,45 Q35,60 15,55', width: 50, height: 80 },
  't': { path: 'M25,15 L25,60 Q30,70 40,65 M15,30 L35,30', width: 50, height: 80 },
  'u': { path: 'M10,30 L10,55 Q15,70 30,65 Q45,60 50,45 L50,70', width: 60, height: 80 },
  'v': { path: 'M10,30 Q20,60 30,65 Q40,60 50,30', width: 60, height: 80 },
  'w': { path: 'M10,30 Q15,60 25,65 Q30,60 35,45 Q40,60 45,65 Q55,60 60,30', width: 70, height: 80 },
  'x': { path: 'M10,30 L50,70 M50,30 L10,70', width: 60, height: 80 },
  'y': { path: 'M10,30 Q20,60 30,65 Q40,60 50,30 L45,70 Q40,85 25,80', width: 60, height: 100 },
  'z': { path: 'M15,35 L45,35 L10,65 L50,65', width: 60, height: 80 },
  ' ': { path: '', width: 30, height: 80 },
}

export function generateHandwritingPath(text: string): { path: string; width: number; height: number } {
  let fullPath = ''
  let totalWidth = 0
  const maxHeight = 100
  let currentX = 0

  for (const char of text.toLowerCase()) {
    const letterData = letterPaths[char] || letterPaths['o'] // Default to 'o' for unknown chars
    
    if (letterData.path) {
      // Transform the path to the current position
      const transformedPath = letterData.path.replace(
        /([ML])(\d+),(\d+)/g,
        (_, command, x, y) => `${command}${parseInt(x) + currentX},${y}`
      ).replace(
        /([QC])(\d+),(\d+)\s+(\d+),(\d+)/g,
        (_, command, x1, y1, x2, y2) => 
          `${command}${parseInt(x1) + currentX},${y1} ${parseInt(x2) + currentX},${y2}`
      ).replace(
        /([QC])(\d+),(\d+)\s+(\d+),(\d+)\s+(\d+),(\d+)/g,
        (_, command, x1, y1, x2, y2, x3, y3) => 
          `${command}${parseInt(x1) + currentX},${y1} ${parseInt(x2) + currentX},${y2} ${parseInt(x3) + currentX},${y3}`
      )

      if (fullPath && char !== ' ') {
        fullPath += ' M' + (currentX + 10) + ',50 ' // Connect letters
      }
      fullPath += (fullPath ? ' ' : '') + transformedPath
    }
    
    currentX += letterData.width + 5 // Add spacing between letters
    totalWidth = currentX
  }

  return {
    path: fullPath,
    width: Math.max(totalWidth, 100),
    height: maxHeight
  }
}