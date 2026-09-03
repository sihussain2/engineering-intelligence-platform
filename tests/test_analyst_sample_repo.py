"""Realistic analyst test using sample repository."""

from pathlib import Path
import tempfile

import pytest

from eip.analyst.analyzer import RepositoryAnalyst
from eip.analyst.result import Confidence
from eip.repository.tool import RepositoryTool
from eip.llm.mock import MockLLMClient


class TestAnalystWithSampleRepository:
    """Test analyst with realistic sample repository."""

    def create_ecommerce_repo(self, tmp_path: Path):
        """Create a sample e-commerce repository."""
        # Create main structure
        (tmp_path / "README.md").write_text(
            """# E-Commerce Platform
A sample e-commerce platform with product management, user accounts, and shopping cart.
"""
        )
        (tmp_path / "pyproject.toml").write_text(
            """[project]
name = "ecommerce"
version = "0.1.0"
"""
        )

        # Create source code
        src = tmp_path / "src" / "ecommerce"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("__version__ = '0.1.0'\n")

        # Core modules
        (src / "models.py").write_text(
            """
class User:
    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.is_active = True

class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        self.inventory = 0

class Order:
    def __init__(self, user, items):
        self.user = user
        self.items = items
        self.total = sum(item.price for item in items)
"""
        )

        (src / "services.py").write_text(
            """
from models import User, Order

class UserService:
    def create_user(self, username, email):
        return User(username, email)
    
    def authenticate(self, username, password):
        # TODO: Implement real auth
        pass

class OrderService:
    def create_order(self, user, items):
        return Order(user, items)
    
    def calculate_total(self, order):
        return order.total
"""
        )

        (src / "api.py").write_text(
            """
from services import UserService, OrderService

user_service = UserService()
order_service = OrderService()

def get_user(user_id):
    # GET /users/{user_id}
    pass

def create_order(user_id, items):
    # POST /orders
    pass
"""
        )

        # Tests
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_models.py").write_text(
            """
def test_user_creation():
    pass

def test_product_creation():
    pass

def test_order_creation():
    pass
"""
        )
        (tests / "test_services.py").write_text(
            """
def test_user_service():
    pass

def test_order_service():
    pass
"""
        )

        return tmp_path

    def test_analyst_on_ecommerce_repo(self, tmp_path: Path):
        """Test analyst analyzing a feature on e-commerce repo."""
        repo_path = self.create_ecommerce_repo(tmp_path)
        repo_tool = RepositoryTool(repo_path)

        # Mock LLM response simulating real analysis
        mock_response = {
            "content": """
Let me analyze this requirement to add payment processing to the e-commerce platform.

First, I'll explore the repository structure to understand the codebase...
- Found main models: User, Product, Order
- Found services: UserService, OrderService
- API endpoints exist

Now let me search for payment-related code...
- No existing payment implementation found
- Order model exists but has no payment info
- Services handle order creation but not payment

Let me review the API structure...
- API layer exists in api.py
- Services are decoupled from models
- Good foundation for adding payment service

Based on my analysis:

FINAL_ANALYSIS:
affected_files: [src/ecommerce/models.py, src/ecommerce/services.py, src/ecommerce/api.py, tests/test_services.py]
affected_components: [Order class, OrderService, API layer]
scope: module
complexity: 6
risks: [Integration with external payment provider, Security of payment data, Transaction handling]
implementation_steps: [Add payment fields to Order model, Create PaymentService class, Add payment API endpoints, Add payment tests, Integrate with payment provider]
verification_tests: [test_payment_creation, test_payment_processing, test_payment_error_handling, test_payment_validation]
confidence: high
open_questions: [Which payment provider?, How to handle PCI compliance?, How to store payment history?]
""",
            "tool_calls": [],
            "done": True,
        }

        mock_llm = MockLLMClient(responses=[mock_response])
        analyst = RepositoryAnalyst(repo_tool, llm_client=mock_llm)

        result = analyst.analyze(
            "Add payment processing to the e-commerce platform"
        )

        # Verify comprehensive analysis
        assert result.requirement == "Add payment processing to the e-commerce platform"
        assert result.confidence == Confidence.HIGH
        
        # Check impact analysis
        assert len(result.impact_analysis.affected_files) == 4
        assert "models.py" in " ".join(result.impact_analysis.affected_files)
        assert result.impact_analysis.scope == "module"
        assert result.impact_analysis.estimated_complexity == 6

        # Check identified components
        assert "Order" in " ".join(result.impact_analysis.affected_components)

        # Check risks were identified
        assert len(result.identified_risks) >= 3
        risk_descriptions = " ".join(r.description for r in result.identified_risks)
        assert "payment" in risk_descriptions.lower()

        # Check implementation plan
        assert len(result.implementation_steps) >= 5
        steps_text = " ".join(s.description for s in result.implementation_steps)
        assert "payment" in steps_text.lower()

        # Check verification plan
        assert len(result.verification_plan.unit_tests) >= 4
        tests_text = " ".join(result.verification_plan.unit_tests)
        assert "payment" in tests_text.lower()

        # Check open questions
        assert len(result.open_questions) >= 3
        questions_text = " ".join(result.open_questions)
        assert "provider" in questions_text.lower() or "payment" in questions_text.lower()

    def test_analyst_with_incremental_tool_calls(self, tmp_path: Path):
        """Test analyst performing incremental repository exploration."""
        repo_path = self.create_ecommerce_repo(tmp_path)
        repo_tool = RepositoryTool(repo_path)

        # Simulate agent making multiple tool calls
        responses = [
            {
                "content": "I'll help you add email notifications. Let me first explore the repository structure.",
                "tool_calls": [
                    {"tool_id": "repo.list_files", "arguments": {"path": "src/ecommerce"}}
                ],
                "done": False,
            },
            {
                "content": "Now let me search for existing notification or email code.",
                "tool_calls": [
                    {"tool_id": "repo.search_code", "arguments": {"query": "email", "max_results": 20}}
                ],
                "done": False,
            },
            {
                "content": "Let me check the services to understand the architecture.",
                "tool_calls": [
                    {"tool_id": "repo.read_file", "arguments": {"path": "src/ecommerce/services.py"}}
                ],
                "done": False,
            },
            {
                "content": """
Based on my investigation, here's the analysis for adding email notifications:

FINAL_ANALYSIS:
affected_files: [src/ecommerce/services.py, tests/test_services.py]
affected_components: [UserService, OrderService]
scope: module
complexity: 4
risks: [Email delivery reliability, Spam filtering]
implementation_steps: [Create EmailService, Integrate with UserService, Integrate with OrderService, Add email templates]
verification_tests: [test_email_sending, test_email_formatting]
confidence: medium
open_questions: [Email provider selection?, SMTP configuration?]
""",
                "tool_calls": [],
                "done": True,
            },
        ]

        mock_llm = MockLLMClient(responses=responses)
        analyst = RepositoryAnalyst(repo_tool, llm_client=mock_llm)

        result = analyst.analyze("Add email notifications for user actions")

        # Verify analysis succeeded with tool calls
        assert result.requirement == "Add email notifications for user actions"
        assert result.confidence == Confidence.MEDIUM
        assert len(result.open_questions) >= 2

    def test_analyst_distinguishes_evidence_from_assumptions(self, tmp_path: Path):
        """Test that analyst properly identifies open questions for uncertain facts."""
        repo_path = self.create_ecommerce_repo(tmp_path)
        repo_tool = RepositoryTool(repo_path)

        mock_response = {
            "content": """
Analyzing the requirement to add multi-currency support...

After exploring the codebase, here's what I found:
- Prices are stored as simple numeric values (could be single currency)
- No currency fields in Product or Order models
- No existing multi-currency logic found

FINAL_ANALYSIS:
affected_files: [src/ecommerce/models.py, src/ecommerce/services.py]
affected_components: [Product, Order, OrderService]
scope: module
complexity: 7
risks: [Currency conversion accuracy, Exchange rate management]
implementation_steps: [Add currency field to Product, Add conversion logic, Update Order calculations]
verification_tests: [test_currency_handling, test_conversion_accuracy]
confidence: medium
open_questions: [How many currencies to support?, Real-time exchange rates or cached?, Which exchange rate provider?, Database schema changes needed?]
""",
            "tool_calls": [],
            "done": True,
        }

        mock_llm = MockLLMClient(responses=[mock_response])
        analyst = RepositoryAnalyst(repo_tool, llm_client=mock_llm)

        result = analyst.analyze("Add multi-currency support")

        # Verify open questions are captured
        assert len(result.open_questions) >= 4
        # These should be genuine uncertainties from the analysis
        questions_text = " ".join(result.open_questions)
        assert "currency" in questions_text.lower() or "exchange" in questions_text.lower()

    def test_analyst_with_fixture_sample_repo(self):
        """Test analyst using pytest temp directory as sample repo."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            repo_path = self.create_ecommerce_repo(tmp_path)
            repo_tool = RepositoryTool(repo_path)

            # Verify the repo can be read
            files = repo_tool.list_files()
            assert len(files) > 0

            # Basic analysis without LLM
            analyst = RepositoryAnalyst(repo_tool, llm_client=None)
            result = analyst.analyze("Test requirement")

            assert result.requirement == "Test requirement"
            assert result.confidence == Confidence.LOW
