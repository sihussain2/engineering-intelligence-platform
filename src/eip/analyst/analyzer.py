"""Repository analyst component for requirements analysis."""

import json
import re
from typing import Any, Optional

from eip.repository.tool import RepositoryTool
from eip.llm.protocol import LLMClient
from eip.llm.agent import SimpleAgent
from eip.analyst.result import (
    RepositoryAnalystResult,
    Confidence,
    ComponentInfo,
    ComponentType,
    FileReference,
    ImpactAnalysis,
    VerificationPlan,
    Risk,
    RiskSeverity,
    ImplementationStep,
)


class RepositoryAnalyst:
    """
    LLM-driven analyzer of software requirements against a repository.

    Uses a SimpleAgent with repository tools to:
    - Explore repository structure autonomously
    - Understand implementation details
    - Identify affected files and components
    - Produce structured analysis results

    MILESTONE 3 (Current): LLM-driven repository analysis
    - ✅ Uses existing SimpleAgent for LLM interaction
    - ✅ Leverages repository tools (list_files, read_file, search_code)
    - ✅ Preserves Copilot tool allowlisting behavior
    - ✅ Parses LLM response into structured RepositoryAnalystResult
    - ✅ Handles malformed/incomplete responses gracefully
    - ✅ No new external dependencies
    - ✅ Read-only repository analysis
    """

    def __init__(
        self,
        repository_tool: RepositoryTool,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize the analyst with a repository tool and optional LLM client.

        Args:
            repository_tool: RepositoryTool instance for repository access.
            llm_client: Optional LLMClient for analysis. If None, analysis will
                return a basic structural understanding without LLM-driven investigation.
        """
        if not isinstance(repository_tool, RepositoryTool):
            raise TypeError("repository_tool must be a RepositoryTool instance")
        self.repository_tool = repository_tool
        self.llm_client = llm_client

    def analyze(self, requirement: str) -> RepositoryAnalystResult:
        """
        Analyze a software requirement against the repository.

        Args:
            requirement: Description of the software requirement.

        Returns:
            RepositoryAnalystResult with analysis findings.

        Raises:
            ValueError: If requirement is empty.
        """
        if not requirement:
            raise ValueError("requirement cannot be empty")

        # Generate repository understanding
        repo_understanding = self._get_repository_understanding()

        # If LLM is available, run LLM-driven analysis
        if self.llm_client:
            return self._analyze_with_llm(requirement, repo_understanding)

        # Fallback: basic structural analysis without LLM
        return RepositoryAnalystResult(
            requirement=requirement,
            repository_understanding=repo_understanding,
            impact_analysis=ImpactAnalysis(),
            verification_plan=VerificationPlan(),
            confidence=Confidence.LOW,
        )

    def _get_repository_understanding(self) -> str:
        """
        Get initial understanding of the repository structure.

        Returns:
            String description of repository structure and purpose.
        """
        try:
            # Get root directory contents
            root_files = self.repository_tool.list_files(".")
            file_count = len(root_files)

            # Look for key markers
            has_readme = any("README" in f for f in root_files)
            has_pyproject = any("pyproject.toml" in f for f in root_files)
            has_setup = any("setup.py" in f or "setup.cfg" in f for f in root_files)
            has_tests = any("test" in f.lower() for f in root_files)
            has_src = any("src" in f for f in root_files)
            has_docs = any("doc" in f.lower() for f in root_files)

            parts = [f"Repository has {file_count} top-level items."]

            if has_src or has_pyproject or has_setup:
                parts.append("Python project structure detected.")
            if has_readme:
                parts.append("Project documentation (README) present.")
            if has_tests:
                parts.append("Test suite present.")
            if has_docs:
                parts.append("Documentation directory present.")

            return " ".join(parts)
        except Exception as e:
            return f"Repository exploration attempted. Error: {str(e)}"

    def _analyze_with_llm(
        self, requirement: str, repo_understanding: str
    ) -> RepositoryAnalystResult:
        """
        Run LLM-driven analysis using SimpleAgent.

        Args:
            requirement: The software requirement.
            repo_understanding: Initial repository understanding.

        Returns:
            RepositoryAnalystResult with LLM-driven findings.
        """
        try:
            # Create agent
            agent = SimpleAgent(
                llm_client=self.llm_client,
                repository_tool=self.repository_tool,
                max_iterations=10,
            )

            # Create system prompt that guides analysis
            system_prompt = self._create_analysis_system_prompt()

            # Create requirement message
            analysis_request = self._create_analysis_request(requirement, repo_understanding)

            # Run agent
            session = agent.run(analysis_request, system_prompt=system_prompt)

            # Parse results from final response
            result = self._parse_agent_response(
                requirement, repo_understanding, session
            )

            return result

        except Exception as e:
            # Fallback on any error
            return RepositoryAnalystResult(
                requirement=requirement,
                repository_understanding=f"{repo_understanding} [LLM analysis failed: {str(e)}]",
                confidence=Confidence.LOW,
            )

    def _create_analysis_system_prompt(self) -> str:
        """
        Create system prompt for LLM to guide analysis.

        Returns:
            System prompt string.
        """
        return (
            "You are an expert software engineer analyzing a software requirement against a repository. "
            "Your job is to understand the codebase and produce a detailed analysis.\n\n"
            "IMPORTANT: You MUST use the provided tools to investigate the repository. "
            "Do not make assumptions. Only report what you find through the tools.\n\n"
            "Available tools:\n"
            "- list_files(path): Explore directory structure\n"
            "- read_file(path): Read file contents\n"
            "- search_code(query): Find code patterns and text\n\n"
            "TOOL USAGE PROCESS:\n"
            "1. START by exploring repository structure with list_files\n"
            "2. SEARCH for relevant code patterns with search_code\n"
            "3. READ key files with read_file to understand implementation\n"
            "4. ANALYZE all findings to understand affected components\n"
            "5. DETERMINE implementation scope (local/module/platform)\n"
            "6. IDENTIFY risks and dependencies from your findings\n"
            "7. CREATE implementation steps based on repository evidence\n"
            "8. PLAN verification tests based on code structure\n\n"
            "CRITICAL: After using each tool, analyze the results immediately. "
            "Each tool result provides information needed for the next step. "
            "Continue using tools until you have enough information to produce the final analysis.\n\n"
            "FINAL OUTPUT REQUIREMENT:\n"
            "After thorough investigation, provide FINAL_ANALYSIS with this exact format:\n"
            "```\n"
            "FINAL_ANALYSIS:\n"
            "affected_files: [files found in repository that need changes]\n"
            "affected_components: [classes/functions/modules found in repository]\n"
            "scope: local|module|platform|unknown\n"
            "complexity: 1-10\n"
            "risks: [risks identified from repository structure]\n"
            "implementation_steps: [steps to implement, based on repository findings]\n"
            "verification_tests: [tests to write, based on code structure]\n"
            "confidence: high|medium|low\n"
            "open_questions: [unknowns from repository]\n"
            "```\n\n"
            "VALIDATION:\n"
            "- Do NOT claim to have tool access if you did not use tools\n"
            "- Do NOT make up file paths or class names\n"
            "- Do NOT report 'unknown scope' if you successfully explored the repository\n"
            "- Report only what you found through tools\n"
            "- If you cannot find something, note it as an open question"
        )


    def _create_analysis_request(self, requirement: str, repo_understanding: str) -> str:
        """
        Create analysis request message.

        Args:
            requirement: The software requirement.
            repo_understanding: Repository understanding.

        Returns:
            Analysis request string.
        """
        return (
            f"REPOSITORY CONTEXT:\n"
            f"{repo_understanding}\n\n"
            f"REQUIREMENT TO ANALYZE:\n"
            f"{requirement}\n\n"
            f"YOUR TASK:\n"
            f"1. You have access to repository tools (list_files, read_file, search_code)\n"
            f"2. Use these tools to explore the repository and understand how to implement this requirement\n"
            f"3. Do NOT proceed without exploring - the repository content is essential\n"
            f"4. Analyze all findings to determine which files, components, and interfaces are affected\n"
            f"5. Based on your findings, create a detailed implementation plan\n"
            f"6. Document risks and testing strategy based on what you discovered\n"
            f"7. Provide your analysis in the FINAL_ANALYSIS format\n\n"
            f"VERIFICATION CHECKLIST:\n"
            f"- ✓ Used list_files to explore directory structure\n"
            f"- ✓ Used search_code to find relevant patterns\n"
            f"- ✓ Used read_file to examine implementation details\n"
            f"- ✓ Identified actual files and components from repository\n"
            f"- ✓ Based analysis on repository evidence, not assumptions\n"
            f"- ✓ Provided FINAL_ANALYSIS in the required format\n\n"
            f"Begin by exploring the repository structure."
        )


    def _parse_agent_response(
        self, requirement: str, repo_understanding: str, session: Any
    ) -> RepositoryAnalystResult:
        """
        Parse agent's final response into structured result.

        Args:
            requirement: The requirement.
            repo_understanding: Repository understanding.
            session: AgentSession from agent.run().

        Returns:
            RepositoryAnalystResult.
        """
        final_response = session.final_response or ""

        # Try to extract structured section
        structured = self._extract_structured_analysis(final_response)

        # Build result
        result = RepositoryAnalystResult(
            requirement=requirement,
            repository_understanding=repo_understanding,
            impact_analysis=ImpactAnalysis(
                affected_files=structured.get("affected_files", []),
                affected_components=structured.get("affected_components", []),
                scope=structured.get("scope", "unknown"),
                estimated_complexity=structured.get("complexity", 1),
            ),
            implementation_steps=self._parse_implementation_steps(
                structured.get("implementation_steps", [])
            ),
            verification_plan=VerificationPlan(
                unit_tests=structured.get("verification_tests", [])
            ),
            identified_risks=self._parse_risks(structured.get("risks", [])),
            open_questions=structured.get("open_questions", []),
            confidence=self._parse_confidence(structured.get("confidence", "low")),
        )

        return result

    def _extract_structured_analysis(self, response: str) -> dict[str, Any]:
        """
        Extract structured analysis from LLM response.

        Looks for FINAL_ANALYSIS section and parses it.

        Args:
            response: LLM response text.

        Returns:
            Dict with extracted fields (empty dict if nothing found).
        """
        result = {}

        # Try to find FINAL_ANALYSIS section
        match = re.search(r"FINAL_ANALYSIS:?(.*?)(?:$|```)", response, re.DOTALL | re.IGNORECASE)
        if not match:
            return result

        analysis_text = match.group(1)

        # Extract individual fields - be more careful with multi-line content
        result["affected_files"] = self._extract_list(
            analysis_text, r"affected_files\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)"
        )
        result["affected_components"] = self._extract_list(
            analysis_text, r"affected_components\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)"
        )
        result["risks"] = self._extract_list(
            analysis_text, r"risks\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)"
        )
        result["implementation_steps"] = self._extract_list(
            analysis_text, r"implementation_steps\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)"
        )
        result["verification_tests"] = self._extract_list(
            analysis_text, r"verification_tests\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)"
        )
        result["open_questions"] = self._extract_list(
            analysis_text, r"open_questions\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)"
        )

        # Extract scalar fields
        scope_match = re.search(
            r"scope\s*:\s*(local|module|platform|unknown)", analysis_text, re.IGNORECASE
        )
        if scope_match:
            result["scope"] = scope_match.group(1).lower()

        complexity_match = re.search(r"complexity\s*:\s*(\d+)", analysis_text)
        if complexity_match:
            try:
                val = int(complexity_match.group(1))
                result["complexity"] = max(1, min(10, val))  # Clamp to 1-10
            except (ValueError, AttributeError):
                pass

        confidence_match = re.search(
            r"confidence\s*:\s*(high|medium|low)", analysis_text, re.IGNORECASE
        )
        if confidence_match:
            result["confidence"] = confidence_match.group(1).lower()

        return result

    def _extract_list(self, text: str, pattern: str) -> list[str]:
        """
        Extract a list from text using regex pattern.

        Args:
            text: Text to search.
            pattern: Regex pattern with one capture group.

        Returns:
            List of items, or empty list if not found.
        """
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return []

        content = match.group(1).strip()

        # Try to parse as JSON array
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to parse as bracket-delimited list
        bracket_match = re.search(r"\[(.*?)\]", content, re.DOTALL)
        if bracket_match:
            items_text = bracket_match.group(1)
            items = re.split(r"[,\n]", items_text)
            return [item.strip().strip("'\"") for item in items if item.strip()]

        # Try comma-separated
        if "," in content:
            items = content.split(",")
            return [item.strip().strip("'\"") for item in items if item.strip()]

        # Try newline-separated (bullet points, numbered lists, etc)
        lines = content.split("\n")
        items = []
        for line in lines:
            line = line.strip()
            if line:
                # Remove common prefixes: -, *, •, numbered lists, etc
                line = re.sub(r"^[-*•]\s*", "", line)
                line = re.sub(r"^\d+\.\s*", "", line)
                if line:
                    items.append(line)

        return items if items else []

    def _parse_implementation_steps(self, steps_data: list[str]) -> list[ImplementationStep]:
        """
        Convert parsed steps into ImplementationStep objects.

        Args:
            steps_data: List of step descriptions.

        Returns:
            List of ImplementationStep.
        """
        result = []
        for i, step_desc in enumerate(steps_data, start=1):
            try:
                result.append(
                    ImplementationStep(
                        order=i,
                        title=f"Step {i}",
                        description=step_desc,
                        complexity=5,  # Default middle value
                    )
                )
            except (ValueError, AttributeError):
                pass
        return result

    def _parse_risks(self, risks_data: list[str]) -> list[Risk]:
        """
        Convert parsed risks into Risk objects.

        Args:
            risks_data: List of risk descriptions.

        Returns:
            List of Risk.
        """
        result = []
        for risk_desc in risks_data:
            try:
                result.append(
                    Risk(
                        description=risk_desc,
                        severity=RiskSeverity.MEDIUM,  # Default
                        mitigation="Further investigation needed",
                        likelihood=5,  # Default middle value
                    )
                )
            except (ValueError, AttributeError):
                pass
        return result

    def _parse_confidence(self, conf_str: str) -> Confidence:
        """
        Parse confidence level string.

        Args:
            conf_str: Confidence string from LLM.

        Returns:
            Confidence enum value.
        """
        conf_str_lower = conf_str.lower().strip()
        if "high" in conf_str_lower:
            return Confidence.HIGH
        elif "medium" in conf_str_lower:
            return Confidence.MEDIUM
        elif "low" in conf_str_lower:
            return Confidence.LOW
        else:
            return Confidence.UNKNOWN
