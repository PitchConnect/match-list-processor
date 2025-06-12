"""Tests for GitHub Actions workflows."""

from pathlib import Path

import yaml


class TestWorkflows:
    """Test GitHub Actions workflow configurations."""

    @property
    def workflows_dir(self):
        """Get the workflows directory path."""
        return Path(__file__).parent.parent / ".github" / "workflows"

    def test_ci_workflow_exists(self):
        """Test that CI workflow file exists."""
        ci_workflow = self.workflows_dir / "ci.yml"
        assert ci_workflow.exists(), "CI workflow file should exist"

    def test_release_workflow_exists(self):
        """Test that release workflow file exists."""
        release_workflow = self.workflows_dir / "release.yml"
        assert release_workflow.exists(), "Release workflow file should exist"

    def test_ci_workflow_structure(self):
        """Test CI workflow has correct structure."""
        ci_workflow = self.workflows_dir / "ci.yml"
        with open(ci_workflow, "r") as f:
            workflow = yaml.safe_load(f)

        # Check basic structure
        assert "name" in workflow
        assert workflow["name"] == "CI/CD Pipeline"
        assert ("on" in workflow) or (True in workflow), "Workflow should have triggers defined"
        assert "jobs" in workflow

        # Check triggers (handle YAML parsing of 'on' keyword)
        triggers = workflow.get("on") or workflow.get(True)
        assert triggers is not None, "Workflow should have triggers defined"
        assert "pull_request" in triggers
        assert "push" in triggers
        assert "branches" in triggers["push"]
        assert "main" in triggers["push"]["branches"]
        assert "develop" in triggers["push"]["branches"]

        # Check jobs exist
        expected_jobs = ["test", "code-quality", "security", "docker-build"]
        for job in expected_jobs:
            assert job in workflow["jobs"], f"Job '{job}' should exist in CI workflow"

    def test_release_workflow_structure(self):
        """Test release workflow has correct structure."""
        release_workflow = self.workflows_dir / "release.yml"
        with open(release_workflow, "r") as f:
            workflow = yaml.safe_load(f)

        # Check basic structure
        assert "name" in workflow
        assert workflow["name"] == "Container Release"
        assert ("on" in workflow) or (True in workflow), "Workflow should have triggers defined"
        assert "jobs" in workflow

        # Check triggers - should only trigger on version tags (handle YAML parsing of 'on' keyword)
        triggers = workflow.get("on") or workflow.get(True)
        assert triggers is not None, "Workflow should have triggers defined"
        assert "push" in triggers
        assert "tags" in triggers["push"]
        assert "v*" in triggers["push"]["tags"]

        # Check environment variables
        assert "env" in workflow
        assert "REGISTRY" in workflow["env"]
        assert workflow["env"]["REGISTRY"] == "ghcr.io"
        assert "IMAGE_NAME" in workflow["env"]
        assert workflow["env"]["IMAGE_NAME"] == "pitchconnect/match-list-processor"

        # Check release job exists
        assert "release" in workflow["jobs"]
        release_job = workflow["jobs"]["release"]

        # Check permissions
        assert "permissions" in release_job
        permissions = release_job["permissions"]
        required_permissions = ["contents", "packages", "attestations", "id-token"]
        for perm in required_permissions:
            assert perm in permissions

    def test_docker_build_job_structure(self):
        """Test docker-build job in CI workflow has correct structure."""
        ci_workflow = self.workflows_dir / "ci.yml"
        with open(ci_workflow, "r") as f:
            workflow = yaml.safe_load(f)

        docker_job = workflow["jobs"]["docker-build"]
        assert "runs-on" in docker_job
        assert docker_job["runs-on"] == "ubuntu-latest"
        assert "steps" in docker_job

        # Check required steps exist
        step_names = [step.get("name", "") for step in docker_job["steps"]]
        required_steps = [
            "Checkout code",
            "Set up Docker Buildx",
            "Build Docker image",
            "Test Docker image",
        ]

        for required_step in required_steps:
            assert any(
                required_step in step_name for step_name in step_names
            ), f"Step '{required_step}' should exist in docker-build job"

    def test_release_job_structure(self):
        """Test release job in release workflow has correct structure."""
        release_workflow = self.workflows_dir / "release.yml"
        with open(release_workflow, "r") as f:
            workflow = yaml.safe_load(f)

        release_job = workflow["jobs"]["release"]
        assert "runs-on" in release_job
        assert release_job["runs-on"] == "ubuntu-latest"
        assert "steps" in release_job

        # Check required steps exist
        step_names = [step.get("name", "") for step in release_job["steps"]]
        required_steps = [
            "Checkout code",
            "Set up Docker Buildx",
            "Log in to GitHub Container Registry",
            "Extract metadata",
            "Build and push Docker image",
            "Generate artifact attestation",
            "Create GitHub Release",
        ]

        for required_step in required_steps:
            assert any(
                required_step in step_name for step_name in step_names
            ), f"Step '{required_step}' should exist in release job"

    def test_workflow_yaml_syntax(self):
        """Test that all workflow files have valid YAML syntax."""
        for workflow_file in self.workflows_dir.glob("*.yml"):
            with open(workflow_file, "r") as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    assert False, f"Invalid YAML syntax in {workflow_file.name}: {e}"

    def test_docker_actions_versions(self):
        """Test that Docker-related actions use appropriate versions."""
        release_workflow = self.workflows_dir / "release.yml"
        with open(release_workflow, "r") as f:
            workflow = yaml.safe_load(f)

        release_job = workflow["jobs"]["release"]

        # Check for modern action versions
        for step in release_job["steps"]:
            if "uses" in step:
                action = step["uses"]
                if "docker/setup-buildx-action" in action:
                    assert "@v3" in action, "Should use docker/setup-buildx-action@v3 or later"
                elif "docker/login-action" in action:
                    assert "@v3" in action, "Should use docker/login-action@v3 or later"
                elif "docker/build-push-action" in action:
                    assert "@v5" in action, "Should use docker/build-push-action@v5 or later"
                elif "docker/metadata-action" in action:
                    assert "@v5" in action, "Should use docker/metadata-action@v5 or later"

    def test_container_registry_configuration(self):
        """Test container registry is properly configured."""
        release_workflow = self.workflows_dir / "release.yml"
        with open(release_workflow, "r") as f:
            workflow = yaml.safe_load(f)

        # Check environment variables
        assert workflow["env"]["REGISTRY"] == "ghcr.io"
        assert "pitchconnect" in workflow["env"]["IMAGE_NAME"].lower()
        assert "match-list-processor" in workflow["env"]["IMAGE_NAME"]

        # Check login step configuration
        release_job = workflow["jobs"]["release"]
        login_step = None
        for step in release_job["steps"]:
            if step.get("name") == "Log in to GitHub Container Registry":
                login_step = step
                break

        assert login_step is not None, "Login step should exist"
        assert "with" in login_step
        assert login_step["with"]["registry"] == "${{ env.REGISTRY }}"
        assert login_step["with"]["username"] == "${{ github.actor }}"
        assert login_step["with"]["password"] == "${{ secrets.GITHUB_TOKEN }}"
