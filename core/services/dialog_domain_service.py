"""
Dialog Domain Service Module

This module implements the domain service for dialog-related business logic.
It provides a concrete implementation of the IDialogDomainService interface,
which composes a prompt for the language model by combining personality data
with the user's input.

Domain services encapsulate business rules that do not naturally belong
in the entity models themselves, keeping the core domain logic focused and clean.
"""

from typing import Dict

from adapters.loggers.logger_adapter import app_logger
from core.interfaces.dialog_domain_service_interface import \
    IDialogDomainService


class DialogDomainService(IDialogDomainService):
    """
    Domain service for composing dialog prompts that integrate personality data and user input.

    This service generates a detailed prompt with response formatting guidelines
    that help the language model produce responses reflecting the given personality profile.
    """

    def _get_trait_guidance(self, trait: str, value: float) -> str:
        """
        Generate a natural language description for a given personality trait.

        Args:
            trait (str): The name of the personality trait.
            value (float): The normalized trait score (on a 1-5 scale).

        Returns:
            str: A formatted string explaining the trait and its communication implications.
        """
        level = "High" if value >= 4.0 else "Moderate" if value >= 2.5 else "Low"

        trait_guidance = {
            "extraversion": {
                "High": "use enthusiastic language and initiate ideas naturally",
                "Moderate": "maintain balanced social engagement",
                "Low": "prefer deeper one-on-one conversations",
            },
            "agreeableness": {
                "High": "prioritize harmony and use cooperative language",
                "Moderate": "allow polite disagreement when needed",
                "Low": "engage in constructive debate occasionally",
            },
            "conscientiousness": {
                "High": "emphasize structure and practical steps",
                "Moderate": "balance planning with flexibility",
                "Low": "focus on the big picture rather than details",
            },
            "neuroticism": {
                "High": "provide extra emotional support",
                "Moderate": "maintain calm with emotional awareness",
                "Low": "project stable optimism",
            },
            "openness": {
                "High": "explore creative possibilities",
                "Moderate": "balance ideas with practicality",
                "Low": "stick to proven methods",
            },
        }

        base = f"{trait.capitalize()} ({value}/5): {level} - "
        return base + trait_guidance.get(trait.lower(), {}).get(
            level, "adapt communication style appropriately"
        )

    def _get_tone_example(self, persona_data: Dict[str, float]) -> str:
        """
        Generate an example tone description based on the top personality traits.

        Args:
            persona_data (Dict[str, float]): Dictionary of personality trait scores.

        Returns:
            str: An example description of a blended tone.
        """
        traits = sorted(persona_data.items(), key=lambda x: x[1], reverse=True)
        if len(traits) < 2:
            return "balanced professional tone"
        primary, secondary = traits[:2]
        combinations = {
            (
                "extraversion",
                "agreeableness",
            ): f"friendly enthusiasm ({primary[0]} + {secondary[0]})",
            (
                "openness",
                "conscientiousness",
            ): f"structured creativity ({primary[0]} + {secondary[0]})",
            (
                "neuroticism",
                "agreeableness",
            ): f"compassionate support ({primary[0]} + {secondary[0]})",
        }
        return combinations.get(
            (primary[0], secondary[0]), f"balanced {primary[0]}-informed tone"
        )

    def _get_interaction_style(self, persona_data: Dict[str, float]) -> str:
        """
        Determine the interaction style based on the personality profile.

        Args:
            persona_data (Dict[str, float]): Dictionary of personality traits.

        Returns:
            str: A string describing the recommended interaction style.
        """
        styles = []
        if persona_data.get("extraversion", 3) > 4:
            styles.append("initiate follow-up questions")
        if persona_data.get("agreeableness", 3) > 4:
            styles.append("validate the user's perspective")
        if persona_data.get("openness", 3) > 4:
            styles.append("offer creative suggestions")
        return " • ".join(styles) if styles else "respond concisely to direct queries"

    def compose_prompt(self, persona_data: Dict[str, float], user_text: str) -> str:
        """
        Construct a detailed prompt that integrates personality data and the user's message.

        This method generates a prompt that includes:
          - A summary of personality data with natural language guidance.
          - Explicit instructions for tone adaptation, linguistic patterns, and interaction style.
          - The current conversation context with the user's input.

        Args:
            persona_data (Dict[str, float]): Dictionary containing personality traits.
            user_text (str): The text input provided by the user.

        Returns:
            str: The composed prompt to be used by the language model.
        """
        trait_explanations = "\n".join(
            [
                f"• {self._get_trait_guidance(trait, value)}"
                for trait, value in persona_data.items()
            ]
        )

        prompt = f"""## Role Specification
You are a conversational agent designed to naturally embody personality traits through linguistic patterns.

## Personality Profile
{trait_explanations}

## Response Guidelines
1. Tone Adaptation: 
   - Match the emotional valence of dominant traits.
   - Blend traits naturally (e.g. {self._get_tone_example(persona_data)}).
   
2. Linguistic Patterns:
   - Syntax complexity: {"Use varied structures" if persona_data.get('openness', 3) > 3.5 else "Keep sentences direct"}.
   - Vocabulary: {"Rich and metaphorical" if persona_data.get('openness', 3) > 4.0 else "Concrete and literal"}.
   
3. Interaction Style:
   - {self._get_interaction_style(persona_data)}
   
4. Content Focus:
   - Emphasize aspects aligned with dominant traits.
   - Address user needs while maintaining personality.

## Current Conversation
User: "{user_text}"

Generate response that:"""
        app_logger.info("Constructed detailed personality-aware prompt")
        return prompt
