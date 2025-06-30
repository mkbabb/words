"""Anki card template definitions and card types."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CardType(Enum):
    """Types of flashcards that can be generated."""

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    DEFINITION_TO_WORD = "definition_to_word"
    WORD_TO_DEFINITION = "word_to_definition"


class AnkiCardTemplate(BaseModel):
    """Template for generating Anki flashcards."""

    card_type: CardType
    front_template: str
    back_template: str
    css_styles: str
    javascript: str = ""
    fields: list[str] = Field(default_factory=list)

    @classmethod
    def get_multiple_choice_template(cls) -> AnkiCardTemplate:
        """Get template for multiple choice cards."""
        front_template = """
        <div class="card">
            <div class="word-header">
                <h1 class="word">{{Word}}</h1>
                <div class="pronunciation">{{Pronunciation}}</div>
            </div>
            
            <div class="question">
                What does this word mean?
            </div>
            
            <div class="choices">
                <div class="choice" onclick="selectChoice(this, 'A')">
                    <span class="choice-letter">A)</span>
                    <span class="choice-text">{{ChoiceA}}</span>
                </div>
                <div class="choice" onclick="selectChoice(this, 'B')">
                    <span class="choice-letter">B)</span>
                    <span class="choice-text">{{ChoiceB}}</span>
                </div>
                <div class="choice" onclick="selectChoice(this, 'C')">
                    <span class="choice-letter">C)</span>
                    <span class="choice-text">{{ChoiceC}}</span>
                </div>
                <div class="choice" onclick="selectChoice(this, 'D')">
                    <span class="choice-letter">D)</span>
                    <span class="choice-text">{{ChoiceD}}</span>
                </div>
            </div>
            
            <div class="reveal-button">
                <button onclick="revealAnswer()">Show Answer</button>
            </div>
        </div>
        """

        back_template = """
        <div class="card">
            <div class="word-header">
                <h1 class="word">{{Word}}</h1>
                <div class="pronunciation">{{Pronunciation}}</div>
            </div>
            
            <div class="correct-answer">
                <h3>Correct Answer: {{CorrectChoice}}</h3>
                <div class="definition">{{Definition}}</div>
            </div>
            
            <div class="examples">
                <h4>Examples:</h4>
                {{#Examples}}
                <div class="example">{{.}}</div>
                {{/Examples}}
            </div>
            
            <div class="synonyms">
                {{#Synonyms}}
                <span class="synonym">{{.}}</span>
                {{/Synonyms}}
            </div>
        </div>
        """

        css_styles = """
        .card {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            color: white;
        }
        
        .word-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .word {
            font-size: 2.5em;
            font-weight: 700;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .pronunciation {
            font-size: 1.2em;
            opacity: 0.9;
            margin-top: 10px;
            font-style: italic;
        }
        
        .question {
            font-size: 1.3em;
            text-align: center;
            margin-bottom: 25px;
            font-weight: 500;
        }
        
        .choices {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 25px;
        }
        
        .choice {
            background: rgba(255,255,255,0.1);
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
        }
        
        .choice:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }
        
        .choice.selected {
            background: rgba(255,255,255,0.3);
            border-color: #FFD700;
        }
        
        .choice.correct {
            background: rgba(76, 175, 80, 0.3);
            border-color: #4CAF50;
        }
        
        .choice.incorrect {
            background: rgba(244, 67, 54, 0.3);
            border-color: #F44336;
        }
        
        .choice-letter {
            font-weight: bold;
            margin-right: 12px;
            min-width: 25px;
        }
        
        .choice-text {
            flex: 1;
        }
        
        .reveal-button {
            text-align: center;
        }
        
        .reveal-button button {
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.4);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .reveal-button button:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        .correct-answer {
            text-align: center;
            margin-bottom: 25px;
        }
        
        .correct-answer h3 {
            color: #FFD700;
            margin-bottom: 15px;
        }
        
        .definition {
            font-size: 1.2em;
            line-height: 1.5;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
        }
        
        .examples {
            margin-bottom: 20px;
        }
        
        .examples h4 {
            margin-bottom: 10px;
            color: #FFD700;
        }
        
        .example {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-style: italic;
        }
        
        .synonyms {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .synonym {
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        """

        javascript = """
        function selectChoice(element, choice) {
            // Remove previous selections
            document.querySelectorAll('.choice').forEach(c => c.classList.remove('selected'));
            // Mark current selection
            element.classList.add('selected');
            // Store selection for reveal
            window.selectedChoice = choice;
        }
        
        function revealAnswer() {
            const correctChoice = '{{CorrectChoice}}';
            const choices = document.querySelectorAll('.choice');
            
            choices.forEach((choice, index) => {
                const letter = String.fromCharCode(65 + index); // A, B, C, D
                if (letter === correctChoice) {
                    choice.classList.add('correct');
                } else if (window.selectedChoice === letter) {
                    choice.classList.add('incorrect');
                }
            });
            
            // Hide reveal button
            document.querySelector('.reveal-button').style.display = 'none';
        }
        """

        return cls(
            card_type=CardType.MULTIPLE_CHOICE,
            front_template=front_template,
            back_template=back_template,
            css_styles=css_styles,
            javascript=javascript,
            fields=[
                "Word",
                "Pronunciation",
                "ChoiceA",
                "ChoiceB",
                "ChoiceC",
                "ChoiceD",
                "CorrectChoice",
                "Definition",
                "Examples",
                "Synonyms",
            ],
        )

    @classmethod
    def get_fill_in_blank_template(cls) -> AnkiCardTemplate:
        """Get template for fill-in-the-blank cards."""
        front_template = """
        <div class="card">
            <div class="word-header">
                <div class="pronunciation">{{Pronunciation}}</div>
            </div>
            
            <div class="question">
                Fill in the blank:
            </div>
            
            <div class="sentence">
                {{SentenceWithBlank}}
            </div>
            
            <div class="word-type">
                <span class="label">Part of speech:</span> {{WordType}}
            </div>
            
            <div class="hint">
                {{#Hint}}
                <div class="hint-text">💡 {{Hint}}</div>
                {{/Hint}}
            </div>
        </div>
        """

        back_template = """
        <div class="card">
            <div class="word-header">
                <h1 class="word">{{Word}}</h1>
                <div class="pronunciation">{{Pronunciation}}</div>
            </div>
            
            <div class="completed-sentence">
                {{CompleteSentence}}
            </div>
            
            <div class="definition">
                <h4>Definition:</h4>
                {{Definition}}
            </div>
            
            <div class="additional-examples">
                <h4>More Examples:</h4>
                {{#AdditionalExamples}}
                <div class="example">{{.}}</div>
                {{/AdditionalExamples}}
            </div>
        </div>
        """

        css_styles = """
        .card {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            color: white;
        }
        
        .word-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .word {
            font-size: 2.5em;
            font-weight: 700;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .pronunciation {
            font-size: 1.2em;
            opacity: 0.9;
            margin-top: 10px;
            font-style: italic;
        }
        
        .question {
            font-size: 1.3em;
            text-align: center;
            margin-bottom: 25px;
            font-weight: 500;
        }
        
        .sentence {
            font-size: 1.4em;
            text-align: center;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        
        .blank {
            background: rgba(255,255,255,0.3);
            padding: 5px 15px;
            border-radius: 5px;
            border: 2px dashed rgba(255,255,255,0.5);
            min-width: 100px;
            display: inline-block;
            text-align: center;
        }
        
        .word-type {
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.1em;
        }
        
        .label {
            font-weight: bold;
            opacity: 0.8;
        }
        
        .hint {
            text-align: center;
            margin-top: 15px;
        }
        
        .hint-text {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
            font-style: italic;
        }
        
        .completed-sentence {
            font-size: 1.4em;
            text-align: center;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            line-height: 1.6;
        }
        
        .word-highlight {
            background: rgba(255,215,0,0.3);
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        .definition {
            margin-bottom: 20px;
        }
        
        .definition h4 {
            color: #FFD700;
            margin-bottom: 10px;
        }
        
        .definition div {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            line-height: 1.5;
        }
        
        .additional-examples h4 {
            color: #FFD700;
            margin-bottom: 10px;
        }
        
        .example {
            background: rgba(255,255,255,0.1);
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-style: italic;
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
                "Hint",
                "CompleteSentence",
                "Definition",
                "AdditionalExamples",
            ],
        )
