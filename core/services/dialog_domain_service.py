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

from langchain.prompts import PromptTemplate

from adapters.loggers.logger_adapter import app_logger
from core.interfaces.dialog_domain_service_interface import IDialogDomainService


class DialogDomainService(IDialogDomainService):
    """
    Domain service for composing dialog prompts that integrate personality data and user input.

    This service uses a LangChain PromptTemplate to generate a detailed prompt that includes:
      - A role specification.
      - A formatted personality profile with natural language guidance.
      - Detailed response guidelines covering tone adaptation, linguistic patterns,
        interaction style, and content focus.
      - The current conversation context with the user's input.
    """

    def __init__(self):
        self.prompt_template = PromptTemplate(
            input_variables=[
                "persona",
                "user_text",
                "tone_example",
                "interaction_style",
                "linguistic_guidelines",
            ],
            template=(
                "## Role Specification\n"
                "You are a conversational agent designed to naturally embody personality traits through linguistic patterns.\n\n"
                "## Personality Profile\n"
                "{persona}\n\n"
                "## Response Guidelines\n"
                "1. **Tone Adaptation**:\n"
                "   - Match the emotional valence of dominant traits.\n"
                "   - Blend traits naturally (e.g. {tone_example}).\n\n"
                "2. **Linguistic Patterns**:\n"
                "   - Syntax complexity: {linguistic_guidelines}\n\n"
                "3. **Interaction Style**:\n"
                "   - {interaction_style}\n\n"
                "4. **Content Focus**:\n"
                "   - Emphasize aspects aligned with dominant traits.\n"
                "   - Address user needs while maintaining personality.\n\n"
                "## Current Conversation\n"
                'User: "{user_text}"\n\n'
                "Generate response that:"
            ),
        )
        app_logger.info(
            "DialogDomainService initialized with LangChain prompt template."
        )

    def _format_persona(self, persona_data: Dict[str, float]) -> str:
        """
        Format personality data into a string representation.

        Args:
            persona_data (Dict[str, float]): Dictionary containing personality traits.

        Returns:
            str: A formatted string of personality traits.
        """
        return "\n".join(
            [
                f"• {trait.capitalize()} ({value}/5)"
                for trait, value in persona_data.items()
            ]
        )

    def _get_trait_guidance(self, trait: str, value: float) -> str:
        """
        Generate a natural language description for a given personality trait.

        Args:
            trait (str): The name of the personality trait.
            value (float): The normalized trait score (on a 1-5 scale).

        Returns:
            str: A formatted string explaining the trait and its communication implications.
        """
        if isinstance(value, dict):
            value = value.get("value", 0)
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

    def _get_linguistic_guidelines(self, persona_data: Dict[str, float]) -> str:
        """
        Determine linguistic guidelines based on the personality profile.

        Args:
            persona_data (Dict[str, float]): Dictionary of personality traits.

        Returns:
            str: A string describing the recommended syntax complexity and vocabulary.
        """
        syntax = (
            "Use varied structures"
            if persona_data.get("openness", 3) > 3.5
            else "Keep sentences direct"
        )
        vocabulary = (
            "Rich and metaphorical"
            if persona_data.get("openness", 3) > 4.0
            else "Concrete and literal"
        )
        return f"{syntax} | {vocabulary}"

    def compose_prompt(self, persona_data: Dict[str, float], user_text: str) -> str:
        """
        Construct a detailed prompt that integrates personality data and the user's message.

        This method uses a LangChain PromptTemplate to generate the prompt, which includes:
          - A formatted personality profile.
          - An example tone derived from the personality data.
          - The recommended interaction style.
          - Linguistic guidelines for syntax and vocabulary.
          - The current conversation context with the user's input.

        Args:
            persona_data (Dict[str, float]): Dictionary containing personality traits.
            user_text (str): The text input provided by the user.

        Returns:
            str: The composed prompt to be used by the language model.
        """
        persona_str = "\n".join(
            [
                f"• {self._get_trait_guidance(trait, value)}"
                for trait, value in persona_data.items()
            ]
        )
        tone_example = self._get_tone_example(persona_data)
        interaction_style = self._get_interaction_style(persona_data)
        linguistic_guidelines = self._get_linguistic_guidelines(persona_data)
        prompt = self.prompt_template.format(
            persona=persona_str,
            user_text=user_text,
            tone_example=tone_example,
            interaction_style=interaction_style,
            linguistic_guidelines=linguistic_guidelines,
        )
        app_logger.info(
            "Constructed detailed personality-aware prompt using LangChain template."
        )
        app_logger.debug("Constructed prompt: %s", prompt)

        return prompt
