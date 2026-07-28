"""
Unit tests for document loaders and LoaderRegistry.
"""

import pytest
import io

from app.domain.entities.document import DocumentType, SourceSystem
from app.ingestion.loaders.text_loader import TextLoader, HTMLLoader, StructuredDataLoader
from app.ingestion.loaders.code_loader import CodeLoader
from app.ingestion.loaders.atlassian_loader import ConfluenceLoader, JiraLoader
from app.ingestion.loaders.github_loader import GitHubLoader
from app.ingestion.loaders.slack_teams_loader import SlackTeamsLoader
from app.ingestion.loaders.notion_loader import NotionLoader
from app.ingestion.loaders.loader_registry import LoaderRegistry, get_loader_registry


@pytest.mark.unit
@pytest.mark.asyncio
class TestTextLoaders:
    async def test_text_loader_plain(self):
        loader = TextLoader()
        assert loader.supports(".txt")
        docs = await loader.load("Hello world", title="Test Doc")
        assert len(docs) == 1
        assert docs[0].title == "Test Doc"
        assert docs[0].content == "Hello world"
        assert docs[0].document_type == DocumentType.TEXT

    async def test_text_loader_markdown(self):
        loader = TextLoader()
        docs = await loader.load("# Heading\n\nContent", metadata={"file_extension": ".md", "filename": "doc.md"})
        assert docs[0].document_type == DocumentType.MARKDOWN

    async def test_html_loader(self):
        loader = HTMLLoader()
        assert loader.supports(".html")
        html_str = "<html><head><title>Page Title</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        docs = await loader.load(html_str)
        assert docs[0].title == "Page Title"
        assert "Hello" in docs[0].content
        assert "World" in docs[0].content

    async def test_structured_loader_json(self):
        loader = StructuredDataLoader()
        assert loader.supports(".json")
        json_content = '{"name": "test", "value": 123}'
        docs = await loader.load(json_content, metadata={"file_extension": ".json", "filename": "data.json"})
        assert docs[0].document_type == DocumentType.JSON
        assert '"name": "test"' in docs[0].content

    async def test_structured_loader_openapi(self):
        loader = StructuredDataLoader()
        openapi_str = '{"openapi": "3.0.0", "info": {"title": "Petstore API"}}'
        docs = await loader.load(openapi_str, metadata={"file_extension": ".json"})
        assert docs[0].document_type == DocumentType.OPENAPI
        assert "Petstore API" in docs[0].title

    async def test_structured_loader_csv(self):
        loader = StructuredDataLoader()
        csv_str = "name,role\nAlice,Engineer\nBob,DevOps"
        docs = await loader.load(csv_str, metadata={"file_extension": ".csv"})
        assert docs[0].document_type == DocumentType.CSV
        assert "name: Alice" in docs[0].content or "Alice" in docs[0].content


@pytest.mark.unit
@pytest.mark.asyncio
class TestCodeLoader:
    async def test_python_code_detection(self):
        loader = CodeLoader()
        assert loader.supports(".py")
        code = "def hello():\n    print('world')"
        docs = await loader.load(code, metadata={"filename": "app.py", "file_extension": ".py"})
        assert docs[0].document_type == DocumentType.CODE
        assert docs[0].metadata.language == "python"

    async def test_terraform_detection(self):
        loader = CodeLoader()
        tf_code = 'resource "aws_s3_bucket" "b" {\n  bucket = "my-tf-test-bucket"\n}'
        docs = await loader.load(tf_code, metadata={"filename": "main.tf", "file_extension": ".tf"})
        assert docs[0].document_type == DocumentType.TERRAFORM
        assert docs[0].metadata.language == "terraform"

    async def test_k8s_yaml_detection(self):
        loader = CodeLoader()
        k8s_yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: nginx-deployment"
        docs = await loader.load(k8s_yaml, metadata={"filename": "deploy.yaml", "file_extension": ".yaml"})
        assert docs[0].document_type == DocumentType.KUBERNETES


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnterpriseConnectorsLoaders:
    async def test_confluence_loader(self):
        loader = ConfluenceLoader()
        docs = await loader.load("<h1>Architecture</h1><p>Microservices design</p>", metadata={"space": "ENG", "page_id": "123"})
        assert docs[0].document_type == DocumentType.CONFLUENCE
        assert docs[0].metadata.space == "ENG"

    async def test_jira_loader(self):
        loader = JiraLoader()
        json_ticket = '{"key": "PROJ-101", "summary": "Fix auth bug", "description": "JWT expired error"}'
        docs = await loader.load(json_ticket)
        assert docs[0].document_type == DocumentType.JIRA
        assert "PROJ-101" in docs[0].title

    async def test_github_loader_issue(self):
        loader = GitHubLoader()
        issue_json = '{"number": 42, "title": "Memory leak", "body": "Observed in pod"}'
        docs = await loader.load(issue_json, metadata={"item_type": "issue"})
        assert docs[0].document_type == DocumentType.GITHUB_ISSUE
        assert "Issue #42" in docs[0].title

    async def test_slack_loader(self):
        loader = SlackTeamsLoader()
        slack_json = '[{"user": "Alice", "text": "Deploy complete", "ts": "123456"}]'
        docs = await loader.load(slack_json, source_system=SourceSystem.SLACK, metadata={"channel": "deployments"})
        assert docs[0].document_type == DocumentType.SLACK_EXPORT
        assert "Alice: Deploy complete" in docs[0].content


@pytest.mark.unit
class TestLoaderRegistry:
    def test_registry_singleton(self):
        r1 = get_loader_registry()
        r2 = get_loader_registry()
        assert r1 is r2

    def test_auto_loader_selection(self):
        registry = LoaderRegistry()
        loader = registry.get_loader_for_source("test.py", metadata={"file_extension": ".py"})
        assert isinstance(loader, CodeLoader)

        confluence_loader = registry.get_loader_for_source("", source_system=SourceSystem.CONFLUENCE)
        assert isinstance(confluence_loader, ConfluenceLoader)
