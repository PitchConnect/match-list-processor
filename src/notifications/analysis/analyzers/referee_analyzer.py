"""Specialized analyzer for referee assignments."""

from typing import Any, Dict, List

from ..base_analyzer import FieldAnalyzer
from ..models.analysis_models import ChangeContext, ChangeImpact


class RefereeAssignmentAnalyzer(FieldAnalyzer):
    """Specialized analyzer for referee assignments."""

    def can_analyze(self, field_path: str) -> bool:
        """Check if this analyzer can handle referee-related fields."""
        return "domaruppdrag" in field_path.lower() or "referee" in field_path.lower()

    def analyze_change(
        self, field_path: str, prev_value: Any, curr_value: Any, match_context: Dict[str, Any]
    ) -> List[ChangeContext]:
        """Analyze referee assignment changes."""
        changes = []

        prev_referees = self._normalize_referee_list(prev_value)
        curr_referees = self._normalize_referee_list(curr_value)

        # Analyze new assignments
        new_referees = self._find_new_referees(prev_referees, curr_referees)
        for referee in new_referees:
            changes.append(self._create_new_referee_context(referee, field_path, match_context))

        # Analyze removed assignments
        removed_referees = self._find_removed_referees(prev_referees, curr_referees)
        for referee in removed_referees:
            changes.append(self._create_removed_referee_context(referee, field_path, match_context))

        # Analyze modified assignments
        modified_referees = self._find_modified_referees(prev_referees, curr_referees)
        for prev_ref, curr_ref in modified_referees:
            changes.append(
                self._create_modified_referee_context(prev_ref, curr_ref, field_path, match_context)
            )

        return changes

    def _normalize_referee_list(self, referee_data: Any) -> List[Dict[str, Any]]:
        """Normalize referee data to consistent format."""
        if not referee_data:
            return []

        if isinstance(referee_data, list):
            return [dict(ref, index=i) for i, ref in enumerate(referee_data)]
        elif isinstance(referee_data, dict):
            return [dict(referee_data, index=0)]
        else:
            return []

    def _find_new_referees(self, prev_refs: List[Dict], curr_refs: List[Dict]) -> List[Dict]:
        """Find newly assigned referees."""
        new_refs = []
        prev_ids = {
            ref.get("id", f"temp_{ref.get('namn', '')}_{ref.get('uppdragstyp', '')}")
            for ref in prev_refs
        }

        for ref in curr_refs:
            ref_id = ref.get("id", f"temp_{ref.get('namn', '')}_{ref.get('uppdragstyp', '')}")
            if ref_id not in prev_ids:
                new_refs.append(ref)

        return new_refs

    def _find_removed_referees(self, prev_refs: List[Dict], curr_refs: List[Dict]) -> List[Dict]:
        """Find removed referee assignments."""
        removed_refs = []
        curr_ids = {
            ref.get("id", f"temp_{ref.get('namn', '')}_{ref.get('uppdragstyp', '')}")
            for ref in curr_refs
        }

        for ref in prev_refs:
            ref_id = ref.get("id", f"temp_{ref.get('namn', '')}_{ref.get('uppdragstyp', '')}")
            if ref_id not in curr_ids:
                removed_refs.append(ref)

        return removed_refs

    def _find_modified_referees(self, prev_refs: List[Dict], curr_refs: List[Dict]) -> List[tuple]:
        """Find modified referee assignments."""
        modified_refs = []

        # Create lookup by ID
        prev_by_id = {
            ref.get("id", f"temp_{ref.get('namn', '')}_{ref.get('uppdragstyp', '')}"): ref
            for ref in prev_refs
        }
        curr_by_id = {
            ref.get("id", f"temp_{ref.get('namn', '')}_{ref.get('uppdragstyp', '')}"): ref
            for ref in curr_refs
        }

        # Find common IDs with changes
        common_ids = set(prev_by_id.keys()) & set(curr_by_id.keys())

        for ref_id in common_ids:
            prev_ref = prev_by_id[ref_id]
            curr_ref = curr_by_id[ref_id]

            # Check if any fields changed
            if self._referee_has_changes(prev_ref, curr_ref):
                modified_refs.append((prev_ref, curr_ref))

        return modified_refs

    def _referee_has_changes(self, prev_ref: Dict, curr_ref: Dict) -> bool:
        """Check if referee assignment has meaningful changes."""
        # Compare key fields
        key_fields = ["namn", "uppdragstyp", "telefon", "epost"]

        for field in key_fields:
            if prev_ref.get(field) != curr_ref.get(field):
                return True

        return False

    def _create_new_referee_context(
        self, referee: Dict, field_path: str, match_context: Dict
    ) -> ChangeContext:
        """Create context for new referee assignment."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        return ChangeContext(
            field_path=f"domaruppdraglista[{referee.get('index', 0)}]",
            field_display_name="Referee Assignment",
            change_type="added",
            previous_value=None,
            current_value=referee,
            business_impact=ChangeImpact.HIGH,
            urgency=self.assess_urgency(match_date),
            affected_stakeholders=["referees", "coordinators"],
            change_description=f"New referee assigned: {referee.get('namn', 'Unknown')} as {referee.get('uppdragstyp', 'Unknown role')}",
            technical_description=f"Added referee assignment: {referee}",
            user_friendly_description=f"🟢 You've been assigned as {referee.get('uppdragstyp', 'referee')} for {home_team} vs {away_team} on {self.format_date_friendly(match_date)}",
        )

    def _create_removed_referee_context(
        self, referee: Dict, field_path: str, match_context: Dict
    ) -> ChangeContext:
        """Create context for removed referee assignment."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        return ChangeContext(
            field_path=f"domaruppdraglista[{referee.get('index', 0)}]",
            field_display_name="Referee Assignment",
            change_type="removed",
            previous_value=referee,
            current_value=None,
            business_impact=ChangeImpact.HIGH,
            urgency=self.assess_urgency(match_date),
            affected_stakeholders=["referees", "coordinators"],
            change_description=f"Referee assignment removed: {referee.get('namn', 'Unknown')} ({referee.get('uppdragstyp', 'Unknown role')})",
            technical_description=f"Removed referee assignment: {referee}",
            user_friendly_description=f"🔴 Your assignment as {referee.get('uppdragstyp', 'referee')} for {home_team} vs {away_team} has been cancelled",
        )

    def _create_modified_referee_context(
        self, prev_ref: Dict, curr_ref: Dict, field_path: str, match_context: Dict
    ) -> ChangeContext:
        """Create context for modified referee assignment."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        changes_desc = self._describe_referee_changes(prev_ref, curr_ref)

        return ChangeContext(
            field_path=f"domaruppdraglista[{curr_ref.get('index', 0)}]",
            field_display_name="Referee Assignment",
            change_type="modified",
            previous_value=prev_ref,
            current_value=curr_ref,
            business_impact=ChangeImpact.MEDIUM,
            urgency=self.assess_urgency(match_date),
            affected_stakeholders=["referees", "coordinators"],
            change_description=f"Referee assignment modified: {changes_desc}",
            technical_description=f"Modified referee assignment from {prev_ref} to {curr_ref}",
            user_friendly_description=f"🔄 Your assignment details have been updated for {home_team} vs {away_team}: {changes_desc}",
        )

    def _describe_referee_changes(self, prev_ref: Dict, curr_ref: Dict) -> str:
        """Describe what changed in referee assignment."""
        changes = []

        if prev_ref.get("namn") != curr_ref.get("namn"):
            changes.append(
                f"name changed from '{prev_ref.get('namn')}' to '{curr_ref.get('namn')}'"
            )

        if prev_ref.get("uppdragstyp") != curr_ref.get("uppdragstyp"):
            changes.append(
                f"role changed from '{prev_ref.get('uppdragstyp')}' to '{curr_ref.get('uppdragstyp')}'"
            )

        if prev_ref.get("telefon") != curr_ref.get("telefon"):
            changes.append("phone number updated")

        if prev_ref.get("epost") != curr_ref.get("epost"):
            changes.append("email updated")

        return "; ".join(changes) if changes else "assignment details updated"
