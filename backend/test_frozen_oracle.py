import tempfile
import pytest
from pathlib import Path
from backend.state import SquadState
from backend.graph import frozen_oracle_node, route_after_developer, build_squad_graph

def test_frozen_oracle_node_multi_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / 'test_main.py').write_text('def test_main(): pass', encoding='utf-8')
        (tmp_path / 'test_helpers.py').write_text('def test_helper(): pass', encoding='utf-8')
        (tmp_path / 'metadata.json').write_text('{"key": "val"}', encoding='utf-8')
        (tmp_path / 'checksums.sha256').write_text('hash file', encoding='utf-8')
        (tmp_path / 'README.md').write_text('# Doc', encoding='utf-8')
        
        state: SquadState = {
            'frozen_oracle_path': str(tmp_path),
            'iteration_count': 0,
            'run_id': 'test_run_multi'
        } # type: ignore
        
        result = frozen_oracle_node(state)
        assert 'test_files' in result
        # Only test_main.py and test_helpers.py should be loaded
        assert set(result['test_files'].keys()) == {'test_main.py', 'test_helpers.py'}
        assert result['test_files']['test_main.py'] == 'def test_main(): pass'
        assert result['test_files']['test_helpers.py'] == 'def test_helper(): pass'

def test_frozen_oracle_node_missing_dir():
    state: SquadState = {
        'frozen_oracle_path': 'non_existent_directory_12345',
        'iteration_count': 0
    } # type: ignore
    with pytest.raises(FileNotFoundError):
        frozen_oracle_node(state)

def test_frozen_oracle_node_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / 'metadata.json').write_text('{}', encoding='utf-8')
        state: SquadState = {
            'frozen_oracle_path': tmpdir,
            'iteration_count': 0
        } # type: ignore
        with pytest.raises(ValueError, match='Tidak ada berkas test artifact ditemukan'):
            frozen_oracle_node(state)

def test_route_after_developer_with_frozen_oracle():
    state_iter0: SquadState = {
        'iteration_count': 0,
        'test_files': {},
        'frozen_oracle_path': 'some/path'
    } # type: ignore
    assert route_after_developer(state_iter0) == 'frozen_oracle'

    state_standard: SquadState = {
        'iteration_count': 0,
        'test_files': {},
        'frozen_oracle_path': None
    } # type: ignore
    assert route_after_developer(state_standard) == 'tester'

    state_retry: SquadState = {
        'iteration_count': 1,
        'test_files': {'test_main.py': 'content'},
        'frozen_oracle_path': 'some/path'
    } # type: ignore
    assert route_after_developer(state_retry) == 'executor'

def test_graph_has_frozen_oracle_node():
    graph = build_squad_graph()
    assert graph is not None

def test_frozen_oracle_node_dart_prefix():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / 'card_metric_test.dart').write_text('void main() {}', encoding='utf-8')
        state: SquadState = {
            'frozen_oracle_path': str(tmp_path),
            'target_language': 'dart',
            'iteration_count': 0,
            'run_id': 'test_run_dart'
        } # type: ignore
        result = frozen_oracle_node(state)
        assert 'test/card_metric_test.dart' in result['test_files']
        assert result['test_files']['test/card_metric_test.dart'] == 'void main() {}'
