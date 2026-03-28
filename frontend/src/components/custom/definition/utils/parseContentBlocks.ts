import type { ContentBlock, MathBlockData, CodeBlock as CodeBlockType } from '@mkbabb/latex-paper';

/**
 * Parse plain definition text into ContentBlock[] for rich rendering.
 * Detects $$...$$ display math and ```...``` code blocks.
 * Inline $...$ math is handled at render time by PaperContext.renderTitle().
 *
 * Zero-overhead: plain text without delimiters returns [text].
 */
export function parseContentBlocks(text: string): ContentBlock[] {
    if (!text) return [];

    // Quick check: if no special delimiters, return as-is
    if (!text.includes('$$') && !text.includes('```')) {
        return [text];
    }

    const blocks: ContentBlock[] = [];
    // Split on display math ($$...$$) and code blocks (```...```)
    // Process sequentially to maintain order
    const pattern = /(\$\$[\s\S]*?\$\$|```(\w*)\n([\s\S]*?)```)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(text)) !== null) {
        // Add preceding text as paragraph
        const before = text.slice(lastIndex, match.index).trim();
        if (before) {
            blocks.push(before);
        }

        const matched = match[0];
        if (matched.startsWith('$$')) {
            // Display math block
            const tex = matched.slice(2, -2).trim();
            if (tex) {
                const mathBlock: MathBlockData = { tex };
                blocks.push(mathBlock);
            }
        } else if (matched.startsWith('```')) {
            // Code block
            const language = match[2] || undefined;
            const code = match[3] || '';
            const codeBlock: CodeBlockType = {
                code: { code, language },
            };
            blocks.push(codeBlock);
        }

        lastIndex = match.index + matched.length;
    }

    // Add remaining text
    const remaining = text.slice(lastIndex).trim();
    if (remaining) {
        blocks.push(remaining);
    }

    return blocks;
}
