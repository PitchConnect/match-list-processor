"""Tests for the main application."""

from unittest.mock import Mock, patch

from src.app import MatchListProcessorApp, main, setup_logging


class TestMatchListProcessorApp:
    """Test the main application class."""

    def test_fetch_current_matches(self, sample_matches_list):
        """Test fetching current matches."""
        app = MatchListProcessorApp()
        app.api_client = Mock()
        app.api_client.fetch_matches_list.return_value = sample_matches_list

        result = app._fetch_current_matches()

        assert len(result) == 2
        assert 6169105 in result
        assert 6169106 in result

    def test_fetch_current_matches_empty(self):
        """Test fetching current matches when empty."""
        app = MatchListProcessorApp()
        app.api_client = Mock()
        app.api_client.fetch_matches_list.return_value = []

        result = app._fetch_current_matches()

        assert result == {}

    @patch("src.app.MatchListProcessorApp._process_modified_matches")
    @patch("src.app.MatchListProcessorApp._process_removed_matches")
    @patch("src.app.MatchListProcessorApp._process_new_matches")
    def test_process_match_changes(
        self, mock_process_new, mock_process_removed, mock_process_modified, sample_match_data
    ):
        """Test processing match changes."""
        previous = {}
        current = {123: sample_match_data}

        app = MatchListProcessorApp()
        app._process_match_changes(previous, current)

        mock_process_new.assert_called_once()
        mock_process_removed.assert_called_once()
        mock_process_modified.assert_called_once()

    def test_process_new_matches(self, sample_match_data):
        """Test processing new matches."""
        app = MatchListProcessorApp()
        app.match_processor = Mock()

        new_ids = {123}
        current_matches = {123: sample_match_data}

        app._process_new_matches(new_ids, current_matches)

        app.match_processor.process_match.assert_called_once_with(
            sample_match_data, 123, is_new=True
        )

    def test_process_new_matches_empty(self):
        """Test processing new matches when none exist."""
        app = MatchListProcessorApp()
        app.match_processor = Mock()

        app._process_new_matches(set(), {})

        app.match_processor.process_match.assert_not_called()

    def test_process_removed_matches(self, sample_match_data):
        """Test processing removed matches."""
        app = MatchListProcessorApp()

        removed_ids = {123}
        previous_matches = {123: sample_match_data}

        # This should not raise any exceptions
        app._process_removed_matches(removed_ids, previous_matches)

    def test_process_modified_matches(self, sample_match_data):
        """Test processing modified matches."""
        app = MatchListProcessorApp()
        app.match_processor = Mock()

        # Create modified version
        modified_match = sample_match_data.copy()
        modified_match["tid"] = "2025-06-14T16:00:00"

        common_ids = {123}
        previous_matches = {123: sample_match_data}
        current_matches = {123: modified_match}

        app._process_modified_matches(common_ids, previous_matches, current_matches)

        app.match_processor.process_match.assert_called_once_with(
            modified_match, 123, is_new=False, previous_match_data=sample_match_data
        )

    def test_process_modified_matches_no_changes(self, sample_match_data):
        """Test processing modified matches when no actual changes."""
        app = MatchListProcessorApp()
        app.match_processor = Mock()

        common_ids = {123}
        previous_matches = {123: sample_match_data}
        current_matches = {123: sample_match_data}

        app._process_modified_matches(common_ids, previous_matches, current_matches)

        app.match_processor.process_match.assert_not_called()

    def test_save_current_matches(self, sample_matches_list):
        """Test saving current matches."""
        app = MatchListProcessorApp()
        app.data_manager = Mock()

        current_matches = {match["matchid"]: match for match in sample_matches_list}

        app._save_current_matches(current_matches)

        app.data_manager.save_current_matches_raw_json.assert_called_once()


class TestSetupLogging:
    """Test logging setup."""

    @patch("src.app.logging.basicConfig")
    def test_setup_logging_default(self, mock_basic_config):
        """Test default logging setup."""
        setup_logging()

        mock_basic_config.assert_called_once()


class TestMain:
    """Test main function."""

    @patch("src.app.MatchListProcessorApp")
    @patch("src.app.setup_logging")
    def test_main(self, mock_setup_logging, mock_app_class):
        """Test main function execution."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        main()

        mock_setup_logging.assert_called_once()
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()
