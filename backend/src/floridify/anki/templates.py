"""Anki card template definitions and card types."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..utils.logging import get_logger
from .constants import CardType

logger = get_logger(__name__)

__all__ = ["AnkiCardTemplate", "CardType"]


class AnkiCardTemplate(BaseModel):
    """Template for generating Anki flashcards."""

    card_type: CardType
    front_template: str
    back_template: str
    css_styles: str
    javascript: str = ""
    fields: list[str] = Field(default_factory=list)

    @classmethod
    def get_best_describes_template(cls) -> AnkiCardTemplate:
        """Get template for best describes cards."""
        logger.debug("🎯 Creating best describes card template")
        front_template = """
        <div class="card">
            <div class="word-header">
                <h1 class="word">{{Word}}{{#FrequencyDisplay}}<sup class="frequency">{{FrequencyDisplay}}</sup>{{/FrequencyDisplay}}</h1>
                <div class="pronunciation">{{Pronunciation}}</div>
                <div class="word-type">{{WordType}}</div>
            </div>
            
            <div class="question">
                Which definition best describes this word?
            </div>
            
            <div class="choices">
                <div class="choice">
                    <span class="choice-letter">A)</span>
                    <span class="choice-text">{{ChoiceA}}</span>
                </div>
                <div class="choice">
                    <span class="choice-letter">B)</span>
                    <span class="choice-text">{{ChoiceB}}</span>
                </div>
                <div class="choice">
                    <span class="choice-letter">C)</span>
                    <span class="choice-text">{{ChoiceC}}</span>
                </div>
                <div class="choice">
                    <span class="choice-letter">D)</span>
                    <span class="choice-text">{{ChoiceD}}</span>
                </div>
            </div>
            
        </div>
        """

        back_template = """
        <div class="card">
            <div class="word-header">
                <h1 class="word">{{Word}}{{#FrequencyDisplay}}<sup class="frequency">{{FrequencyDisplay}}</sup>{{/FrequencyDisplay}}</h1>
                <div class="pronunciation">{{Pronunciation}}</div>
                <div class="word-type">{{WordType}}</div>
            </div>
            
            <div class="correct-answer">
                <h3>Correct Answer: {{CorrectChoice}}</h3>
            </div>
            
            <div class="definition">
                <h4>Definition:</h4>
                <div class="definition-text">{{Definition}}</div>
            </div>
            
            <div class="examples">
                <h4>Examples:</h4>
                <div class="examples-list">{{Examples}}</div>
            </div>
            
            <div class="synonyms">
                <h4>Synonyms:</h4>
                <div class="synonyms-list">{{Synonyms}}</div>
            </div>
        </div>
        """

        css_styles = """
        .card {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 500px;
            margin: 0 auto;
            padding: 32px;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            color: #1d1d1f;
            border: 1px solid #e8e8ed;
        }
        
        .word-header {
            text-align: center;
            margin-bottom: 24px;
            border-bottom: 1px solid #e8e8ed;
            padding-bottom: 16px;
        }
        
        .word {
            font-size: 2em;
            font-weight: 600;
            margin: 0;
            color: #1d1d1f;
            letter-spacing: -0.01em;
        }
        
        .frequency {
            font-size: 0.6em;
            color: #007aff;
            font-weight: 500;
            margin-left: 4px;
        }
        
        .pronunciation {
            font-size: 1em;
            color: #86868b;
            margin-top: 4px;
            font-weight: 400;
        }
        
        .word-type {
            font-size: 0.9em;
            color: #86868b;
            margin-top: 2px;
            font-style: italic;
        }
        
        .question {
            font-size: 1.1em;
            text-align: center;
            margin-bottom: 20px;
            font-weight: 500;
            color: #424245;
        }
        
        .choices {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 20px;
        }
        
        .choice {
            background: #f5f5f7;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
        }
        
        .choice.selected {
            background: #007aff;
            border-color: #007aff;
            color: white;
        }
        
        .choice.correct {
            background: #30d158;
            border-color: #30d158;
            color: white;
        }
        
        .choice.incorrect {
            background: #ff3b30;
            border-color: #ff3b30;
            color: white;
        }
        
        .choice-letter {
            font-weight: 600;
            margin-right: 12px;
            min-width: 20px;
        }
        
        .choice-text {
            flex: 1;
            font-weight: 400;
        }
        
        .correct-answer {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .correct-answer h3 {
            color: #30d158;
            margin-bottom: 12px;
            font-weight: 600;
        }
        
        .definition {
            margin-bottom: 16px;
        }
        
        .definition h4 {
            margin-bottom: 8px;
            color: #424245;
            font-weight: 600;
            font-size: 1em;
        }
        
        .definition-text {
            font-size: 1.1em;
            line-height: 1.4;
            background: #f5f5f7;
            padding: 16px;
            border-radius: 8px;
            color: #1d1d1f;
        }
        
        .examples {
            margin-bottom: 16px;
        }
        
        .examples h4 {
            margin-bottom: 8px;
            color: #424245;
            font-weight: 600;
            font-size: 1em;
        }
        
        .examples-list {
            background: #f5f5f7;
            padding: 12px;
            border-radius: 8px;
            font-style: italic;
            color: #424245;
            line-height: 1.4;
        }
        
        .synonyms {
            margin-bottom: 16px;
        }
        
        .synonyms h4 {
            margin-bottom: 8px;
            color: #424245;
            font-weight: 600;
            font-size: 1em;
        }
        
        .synonyms-list {
            background: #f5f5f7;
            padding: 8px 12px;
            border-radius: 8px;
            color: #424245;
            font-size: 0.9em;
        }
        """

        javascript = ""

        return cls(
            card_type=CardType.BEST_DESCRIBES,
            front_template=front_template,
            back_template=back_template,
            css_styles=css_styles,
            javascript=javascript,
            fields=[
                "Word",
                "Pronunciation",
                "WordType",
                "ChoiceA",
                "ChoiceB",
                "ChoiceC",
                "ChoiceD",
                "CorrectChoice",
                "Definition",
                "Examples",
                "Synonyms",
                "Frequency",
                "FrequencyDisplay",
            ],
        )

    @classmethod
    def get_fill_in_blank_template(cls) -> AnkiCardTemplate:
        """Get template for fill-in-the-blank cards."""
        logger.debug("📝 Creating fill-in-blank card template")
        front_template = """
        <div class="card">
            <div class="word-header">
                <div class="pronunciation">{{Pronunciation}}</div>
                <div class="word-type">{{WordType}}</div>
            </div>
            
            <div class="question">
                Fill in the blank:
            </div>
            
            <div class="sentence">
                {{SentenceWithBlank}}
            </div>
            
            <div class="choices">
                <div class="choice">
                    <span class="choice-letter">A)</span>
                    <span class="choice-text">{{ChoiceA}}</span>
                </div>
                <div class="choice">
                    <span class="choice-letter">B)</span>
                    <span class="choice-text">{{ChoiceB}}</span>
                </div>
                <div class="choice">
                    <span class="choice-letter">C)</span>
                    <span class="choice-text">{{ChoiceC}}</span>
                </div>
                <div class="choice">
                    <span class="choice-letter">D)</span>
                    <span class="choice-text">{{ChoiceD}}</span>
                </div>
            </div>
        </div>
        """

        back_template = """
        <div class="card">
            <div class="word-header">
                <h1 class="word">{{Word}}{{#FrequencyDisplay}}<sup class="frequency">{{FrequencyDisplay}}</sup>{{/FrequencyDisplay}}</h1>
                <div class="pronunciation">{{Pronunciation}}</div>
                <div class="word-type">{{WordType}}</div>
            </div>
            
            <div class="correct-answer">
                <h3>Correct Answer: {{CorrectChoice}}</h3>
            </div>
            
            <div class="definition">
                <h4>Definition:</h4>
                <div class="definition-text">{{Definition}}</div>
            </div>
            
            <div class="examples">
                <h4>Examples:</h4>
                <div class="examples-list">{{Examples}}</div>
            </div>
            
            <div class="synonyms">
                <h4>Synonyms:</h4>
                <div class="synonyms-list">{{Synonyms}}</div>
            </div>
        </div>
        """

        css_styles = """
        .card {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 500px;
            margin: 0 auto;
            padding: 32px;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            color: #1d1d1f;
            border: 1px solid #e8e8ed;
        }
        
        .word-header {
            text-align: center;
            margin-bottom: 24px;
            border-bottom: 1px solid #e8e8ed;
            padding-bottom: 16px;
        }
        
        .word {
            font-size: 2em;
            font-weight: 600;
            margin: 0;
            color: #1d1d1f;
            letter-spacing: -0.01em;
        }
        
        .frequency {
            font-size: 0.6em;
            color: #007aff;
            font-weight: 500;
            margin-left: 4px;
        }
        
        .pronunciation {
            font-size: 1em;
            color: #86868b;
            margin-top: 4px;
            font-weight: 400;
        }
        
        .word-type {
            font-size: 0.9em;
            color: #86868b;
            margin-top: 2px;
            font-style: italic;
        }
        
        .question {
            font-size: 1.1em;
            text-align: center;
            margin-bottom: 20px;
            font-weight: 500;
            color: #424245;
        }
        
        .sentence {
            font-size: 1.2em;
            text-align: center;
            background: #f5f5f7;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 16px;
            line-height: 1.5;
            color: #1d1d1f;
        }
        
        .blank {
            background: #007aff;
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 500;
            display: inline-block;
            min-width: 80px;
            text-align: center;
        }
        
        .completed-sentence {
            font-size: 1.2em;
            text-align: center;
            background: #f5f5f7;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            line-height: 1.5;
            color: #1d1d1f;
        }
        
        .word-highlight {
            background: #30d158;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        
        
        .examples-list {
            background: #f5f5f7;
            padding: 12px;
            border-radius: 8px;
            font-style: italic;
            color: #424245;
            line-height: 1.4;
        }
        
        .choices {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 20px;
        }
        
        .choice {
            background: #f5f5f7;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
        }
        
        .choice-letter {
            font-weight: 600;
            margin-right: 12px;
            min-width: 20px;
        }
        
        .choice-text {
            flex: 1;
            font-weight: 400;
        }
        
        .correct-answer {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .correct-answer h3 {
            color: #30d158;
            margin-bottom: 12px;
            font-weight: 600;
        }
        """

        return cls(
            card_type=CardType.FILL_IN_BLANK,
            front_template=front_template,
            back_template=back_template,
            css_styles=css_styles,
            fields=[
                "Word",
                "Pronunciation",
                "SentenceWithBlank",
                "WordType",
                "ChoiceA",
                "ChoiceB",
                "ChoiceC",
                "ChoiceD",
                "CorrectChoice",
                "Definition",
                "Examples",
                "Synonyms",
                "Frequency",
                "FrequencyDisplay",
            ],
        )
