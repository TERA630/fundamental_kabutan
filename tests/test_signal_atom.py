import pytest

from app.domain.models.signal_atom import SignalAtom, score_signal_atoms


def test_score_signal_atoms_adds_active_atoms_and_applies_group_cap():
    atoms = (
        SignalAtom("base", True, points=1),
        SignalAtom("ma5_down", True, points=2, group="ma5", group_max_points=3),
        SignalAtom("ma5_slowing", True, points=1, group="ma5", group_max_points=3),
        SignalAtom("ma5_stalling", True, points=1, group="ma5", group_max_points=3),
        SignalAtom("inactive", False, points=10),
    )

    assert score_signal_atoms(atoms) == 4


def test_score_signal_atoms_rejects_inconsistent_group_caps():
    atoms = (
        SignalAtom("one", True, points=1, group="shared", group_max_points=2),
        SignalAtom("two", True, points=1, group="shared", group_max_points=3),
    )

    with pytest.raises(ValueError, match="inconsistent"):
        score_signal_atoms(atoms)
